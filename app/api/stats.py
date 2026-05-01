from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from app.db.database import get_db
from app.models.models import Client, Counter, BodyMetric, Task
import datetime

router = APIRouter()

@router.get("/insights")
async def get_insights(db: AsyncSession = Depends(get_db)):
    clients_res = await db.execute(select(Client))
    clients = clients_res.scalars().all()
    counters_res = await db.execute(select(Counter))
    counters = counters_res.scalars().all()
    body_res = await db.execute(select(BodyMetric).order_by(BodyMetric.date.desc()))
    body = body_res.scalars().first()
    
    total_res = await db.execute(select(Task).filter(Task.archived == False))
    tasks = total_res.scalars().all()
    done = [t for t in tasks if t.completed]
    
    return {
        "clients": clients,
        "counters": counters,
        "body": body,
        "stats": {
            "total": len(tasks),
            "done": len(done),
            "rate": int((len(done)/len(tasks))*100) if tasks else 0
        }
    }

@router.post("/client")
async def add_client(name: str, db: AsyncSession = Depends(get_db)):
    client = Client(name=name, stages_total=6, stages_done=0)
    db.add(client)
    await db.commit()
    return {"status": "ok"}

@router.delete("/client/{client_id}")
async def delete_client(client_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).filter(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client:
        # Create an archived task for history
        archived_task = Task(name=f"Заказ от {client.name}", completed=True, archived=True, created_at=datetime.date.today())
        db.add(archived_task)
        await db.delete(client)
        await db.commit()
    return {"status": "ok"}

@router.post("/client/{client_id}/toggle")
async def toggle_client_stage(client_id: int, stage_idx: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).filter(Client.id == client_id))
    client = result.scalar_one_or_none()
    if client:
        if client.stages_done == stage_idx: client.stages_done = stage_idx - 1
        else: client.stages_done = stage_idx
        await db.commit()
    return {"status": "ok"}

@router.post("/counter")
async def add_counter(name: str, target: int, db: AsyncSession = Depends(get_db)):
    counter = Counter(name=name, target=target, value=0)
    db.add(counter)
    await db.commit()
    return {"status": "ok"}

@router.delete("/counter/{counter_id}")
async def delete_counter(counter_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Counter).filter(Counter.id == counter_id))
    counter = result.scalar_one_or_none()
    if counter:
        await db.delete(counter)
        await db.commit()
    return {"status": "ok"}

@router.post("/counter/{counter_id}/set")
async def set_counter(counter_id: int, value: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Counter).filter(Counter.id == counter_id))
    counter = result.scalar_one_or_none()
    if counter:
        if counter.value == value: counter.value = value - 1
        else: counter.value = value
        await db.commit()
    return {"status": "ok"}

@router.post("/body/workout")
async def toggle_workout(day_index: int, db: AsyncSession = Depends(get_db)):
    body_res = await db.execute(select(BodyMetric).order_by(BodyMetric.date.desc()))
    body = body_res.scalars().first()
    if not body:
        body = BodyMetric(date=datetime.date.today(), weight=53.75, waist=61, hips=89, workout_history=[False]*30)
        db.add(body)
    history = list(body.workout_history)
    if day_index < len(history):
        history[day_index] = not history[day_index]
        body.workout_history = history
        await db.commit()
    return {"status": "ok"}

@router.post("/body/metrics")
async def update_metrics(weight: float, waist: float, hips: float, chest: float, db: AsyncSession = Depends(get_db)):
    today = datetime.date.today()
    body_res = await db.execute(select(BodyMetric).filter(BodyMetric.date == today))
    body = body_res.scalars().first()
    if not body:
        last_res = await db.execute(select(BodyMetric).order_by(BodyMetric.date.desc()))
        last = last_res.scalars().first()
        history = last.workout_history if last else [False]*30
        body = BodyMetric(date=today, workout_history=history)
        db.add(body)
    body.weight, body.waist, body.hips, body.chest = weight, waist, hips, chest
    await db.commit()
    return {"status": "ok"}

@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    metrics_res = await db.execute(select(BodyMetric).order_by(BodyMetric.date.asc()))
    metrics = metrics_res.scalars().all()
    today = datetime.date.today()
    work_history, personal_history, dates = [], [], []
    heatmap_data = {}

    # Получаем данные за последние 84 дня (12 недель) для Heatmap
    for i in range(83, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        # Считаем задачи, выполненные именно в этот день (по created_at для упрощения, так как нет completed_at)
        # В идеале нужно добавить поле completed_at в модель Task
        done_res = await db.execute(select(Task).filter(and_(Task.created_at == day, Task.completed == True)))
        heatmap_data[day_str] = len(done_res.scalars().all())

    # Получаем данные за последние 14 дней для графиков продуктивности
    for i in range(13, -1, -1):
        day = today - datetime.timedelta(days=i)
        
        # Считаем % выполнения на КОНКРЕТНЫЙ день
        # Рабочие
        w_total = await db.execute(select(Task).filter(and_(Task.created_at <= day, Task.is_personal == False)))
        w_done = await db.execute(select(Task).filter(and_(Task.created_at <= day, Task.completed == True, Task.is_personal == False)))
        wt, wd = len(w_total.scalars().all()), len(w_done.scalars().all())
        work_history.append(int((wd/wt)*100) if wt > 0 else 0)
        
        # Личные
        p_total = await db.execute(select(Task).filter(and_(Task.created_at <= day, Task.is_personal == True)))
        p_done = await db.execute(select(Task).filter(and_(Task.created_at <= day, Task.completed == True, Task.is_personal == True)))
        pt, pd = len(p_total.scalars().all()), len(p_done.scalars().all())
        personal_history.append(int((pd/pt)*100) if pt > 0 else 0)
        
        dates.append(day.strftime("%d.%m"))

    return {
        "body": {"dates": [m.date.strftime("%d.%m.%y") for m in metrics], "weight": [m.weight for m in metrics], "target": [56.0] * len(metrics)},
        "tasks": {"dates": dates, "work": work_history, "personal": personal_history},
        "heatmap": heatmap_data
    }

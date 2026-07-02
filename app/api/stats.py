from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from app.db.database import get_db
from app.models.models import Client, Counter, BodyMetric, Task, ContentMetric
import datetime

router = APIRouter()

MONTH_NAMES = ["", "ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ", "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ"]

@router.get("/insights")
async def get_insights(db: AsyncSession = Depends(get_db)):
    today = datetime.date.today()
    clients_res = await db.execute(select(Client))
    clients = clients_res.scalars().all()
    counters_res = await db.execute(select(Counter))
    counters = counters_res.scalars().all()
    
    # Контент за сегодня
    content_res = await db.execute(select(ContentMetric).filter(ContentMetric.date == today))
    content = content_res.scalar_one_or_none()
    if not content:
        content = ContentMetric(date=today, tg=False, reels=False, vk=False)
        db.add(content)
        await db.commit()
    
    # Автоматическое переключение периода для BodyMetric (start_date + target_days)
    body_res = await db.execute(select(BodyMetric).order_by(BodyMetric.date.desc()))
    body = body_res.scalars().first()
    
    current_month_name = MONTH_NAMES[today.month]
    
    if not body:
        # Первый раз — создаём с сегодняшнего дня на 30 дней
        new_body = BodyMetric(
            date=today,
            start_date=today,
            target_days=30,
            weight=53.75,
            waist=61,
            hips=89,
            workout_history=[False] * 30
        )
        db.add(new_body)
        await db.commit()
        body = new_body
    else:
        # Миграция старых записей (без start_date — календарный месяц)
        if body.start_date is None:
            body.start_date = body.date
            body.target_days = 30
            history = list(body.workout_history) if body.workout_history else []
            if len(history) < 30:
                history.extend([False] * (30 - len(history)))
            else:
                history = history[:30]
            body.workout_history = history
            await db.commit()
        
        # Проверяем, не закончился ли текущий период
        period_end = body.start_date + datetime.timedelta(days=body.target_days - 1)
        if period_end < today:
            # Создаём новый период
            new_body = BodyMetric(
                date=today,
                start_date=today,
                target_days=body.target_days or 30,
                weight=body.weight,
                waist=body.waist,
                hips=body.hips or 89,
                chest=body.chest,
                workout_history=[False] * (body.target_days or 30)
            )
            db.add(new_body)
            await db.commit()
            body = new_body
    
    total_res = await db.execute(select(Task).filter(Task.archived == False))
    tasks = total_res.scalars().all()
    done = [t for t in tasks if t.completed]
    
    return {
        "clients": clients,
        "counters": counters,
        "body": body,
        "content": content,
        "month_name": current_month_name,
        "stats": {
            "total": len(tasks),
            "done": len(done),
            "rate": int((len(done)/len(tasks))*100) if tasks else 0
        }
    }

@router.post("/content/toggle")
async def toggle_content(platform: str, date: str = None, db: AsyncSession = Depends(get_db)):
    if date:
        try:
            target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        except:
            target_date = datetime.date.today()
    else:
        target_date = datetime.date.today()
        
    res = await db.execute(select(ContentMetric).filter(ContentMetric.date == target_date))
    content = res.scalar_one_or_none()
    if not content:
        content = ContentMetric(date=target_date)
        db.add(content)
    
    if platform == 'tg': content.tg = not content.tg
    elif platform == 'reels': content.reels = not content.reels
    elif platform == 'vk': content.vk = not content.vk
    
    await db.commit()
    return {"status": "ok"}

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
        archived_task = Task(
            name=f"Заказ от {client.name}", 
            completed=True, 
            archived=True, 
            created_at=datetime.date.today(),
            completed_at=datetime.date.today()
        )
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
        # Создаем запись в архиве задач
        archived_task = Task(
            name=f"Завершено: {counter.name} ({counter.value}/{counter.target})", 
            completed=True, 
            archived=True, 
            created_at=datetime.date.today(),
            completed_at=datetime.date.today()
        )
        db.add(archived_task)
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
async def toggle_workout(date_str: str, db: AsyncSession = Depends(get_db)):
    toggle_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.date.today()
    
    if toggle_date > today:
        return {"status": "error", "detail": "Cannot mark future dates"}
    
    body_res = await db.execute(select(BodyMetric).order_by(BodyMetric.date.desc()))
    body = body_res.scalars().first()
    
    if not body:
        return {"status": "error", "detail": "No body tracker found"}
    
    # Миграция старых записей
    if body.start_date is None:
        body.start_date = body.date
        body.target_days = 30
        history = list(body.workout_history) if body.workout_history else []
        if len(history) < 30:
            history.extend([False] * (30 - len(history)))
        else:
            history = history[:30]
        body.workout_history = history
        await db.commit()
    
    # Проверяем, попадает ли дата в текущий период
    start = body.start_date
    target = body.target_days or 30
    day_index = (toggle_date - start).days
    
    if day_index < 0 or day_index >= target:
        return {"status": "error", "detail": f"Date {date_str} is outside current period ({start} - {start + datetime.timedelta(days=target-1)})"}
    
    history = list(body.workout_history) if body.workout_history else [False] * target
    if len(history) <= day_index:
        # Дополняем если история короче
        history.extend([False] * (day_index - len(history) + 1))
    
    history[day_index] = not history[day_index]
    body.workout_history = history
    await db.commit()
    return {"status": "success", "date": date_str, "day_index": day_index}

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

@router.get("/morning_greeting")
async def get_morning_greeting(db: AsyncSession = Depends(get_db)):
    today = datetime.date.today()
    # 1. Get tasks due today
    tasks_res = await db.execute(select(Task).filter(and_(Task.due_date == today, Task.archived == False, Task.completed == False)))
    due_today = tasks_res.scalars().all()
    
    # 2. Get Freud progress
    freud_res = await db.execute(select(Counter).filter(Counter.name.ilike("%фрейд%")))
    freud = freud_res.scalar_one_or_none()
    
    # 3. Get total pending tasks
    pending_res = await db.execute(select(Task).filter(and_(Task.archived == False, Task.completed == False)))
    pending_count = len(pending_res.scalars().all())
    
    day_names = ["воскресенье", "понедельник", "вторник", "среду", "четверг", "пятницу", "субботу"]
    day_pronouns = ["это", "этот", "этот", "эту", "этот", "эту", "эту"]
    today_idx = (today.weekday() + 1) % 7
    today_name = day_names[today_idx]
    today_pronoun = day_pronouns[today_idx]

    greeting = f"Доброе утро, Полина! ✨ Прекрасный день, чтобы покорить {today_pronoun} {today_name}. Не забудь хорошо позавтракать и сделать упражнения — это база для продуктивного дня! 💪"
    
    hints = []
    if due_today:
        task_names = [t.name for t in due_today[:2]]
        hints.append(f"Сегодня важно: {', '.join(task_names)}" + (" и другие задачи" if len(due_today) > 2 else ""))
    
    if freud and freud.value < freud.target:
        hints.append(f"Твой прогресс по Фрейду: {freud.value}/{freud.target}. Сделаем еще шаг сегодня?")
    
    if pending_count > 15:
        hints.append(f"Ого, в списке {pending_count} задач! Давай сфокусируемся на самом важном.")
    elif pending_count == 0:
        hints.append("В списке пока нет активных задач. Отличный повод что-то запланировать!")
    else:
        hints.append(f"Впереди всего {pending_count} задач. Отличный темп!")

    context_hint = " ".join(hints) if hints else "Пусть этот день будет продуктивным!"
    
    return {"text": f"{greeting} {context_hint}"}

@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    # Фильтруем данные по весу с начала 2026 года
    start_2026 = datetime.date(2026, 1, 1)
    metrics_res = await db.execute(select(BodyMetric).filter(BodyMetric.date >= start_2026).order_by(BodyMetric.date.asc()))
    metrics = metrics_res.scalars().all()
    today = datetime.date.today()
    work_history, personal_history, dates = [], [], []
    content_tg, content_reels, content_vk = [], [], []
    heatmap_data = {}

    for i in range(83, -1, -1):
        day = today - datetime.timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        done_res = await db.execute(select(Task).filter(and_(Task.completed_at == day, Task.completed == True)))
        heatmap_data[day_str] = len(done_res.scalars().all())

    for i in range(13, -1, -1):
        day = today - datetime.timedelta(days=i)
        # Задачи
        w_done_day = await db.execute(select(Task).filter(and_(Task.completed_at == day, Task.completed == True, Task.is_personal == False)))
        work_history.append(len(w_done_day.scalars().all()))
        p_done_day = await db.execute(select(Task).filter(and_(Task.completed_at == day, Task.completed == True, Task.is_personal == True)))
        personal_history.append(len(p_done_day.scalars().all()))
        
        # Контент
        c_res = await db.execute(select(ContentMetric).filter(ContentMetric.date == day))
        c_met = c_res.scalar_one_or_none()
        content_tg.append(1 if c_met and c_met.tg else 0)
        content_reels.append(1 if c_met and c_met.reels else 0)
        content_vk.append(1 if c_met and c_met.vk else 0)
        
        dates.append(day.strftime("%d.%m"))

    # ... (старый код тренировок)
    prev_month_start = (today.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
    prev_month_end = today.replace(day=1) - datetime.timedelta(days=1)
    
    prev_month_res = await db.execute(select(BodyMetric).filter(and_(
        BodyMetric.date >= prev_month_start,
        BodyMetric.date <= prev_month_end
    )))
    all_prev_metrics = prev_month_res.scalars().all()
    
    workout_stats = {"done": 0, "total": 0, "month": MONTH_NAMES[prev_month_end.month], "history": []}
    if all_prev_metrics:
        best_record = max(all_prev_metrics, key=lambda m: sum(1 for d in (m.workout_history or []) if d))
        history_list = best_record.workout_history or []
        workout_stats["done"] = sum(1 for d in history_list if d)
        workout_stats["total"] = len(history_list)
        workout_stats["history"] = history_list

    monthly_workout_stats = []
    for m_idx in range(1, 13):
        m_start = datetime.date(today.year, m_idx, 1)
        import calendar
        _, last_day = calendar.monthrange(today.year, m_idx)
        m_end = datetime.date(today.year, m_idx, last_day)
        m_res = await db.execute(select(BodyMetric).filter(and_(BodyMetric.date >= m_start, BodyMetric.date <= m_end)))
        m_metrics = m_res.scalars().all()
        if m_metrics:
            best_m = max(m_metrics, key=lambda x: sum(1 for d in x.workout_history if d))
            done = sum(1 for d in (best_m.workout_history or []) if d)
            total = len(best_m.workout_history or [])
            monthly_workout_stats.append({"month": MONTH_NAMES[m_idx], "percent": int((done/total)*100) if total > 0 else 0})
        elif m_idx <= today.month:
            monthly_workout_stats.append({"month": MONTH_NAMES[m_idx], "percent": 0})

    return {
        "body": {"dates": [m.date.strftime("%d.%m.%y") for m in metrics], "weight": [m.weight for m in metrics], "target": [56.0] * len(metrics)},
        "tasks": {"dates": dates, "work": work_history, "personal": personal_history},
        "content_history": {"dates": dates, "tg": content_tg, "reels": content_reels, "vk": content_vk},
        "heatmap": heatmap_data,
        "prev_workout": workout_stats,
        "monthly_workouts": monthly_workout_stats,
        "current_month": MONTH_NAMES[today.month]
    }

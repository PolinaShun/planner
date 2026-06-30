from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
import datetime
from typing import Optional, List

router = APIRouter()

def _task_to_dict(t):
    """Convert Task ORM object to dict for JSON response."""
    def _d(v):
        return v.isoformat() if v is not None else None
    return {
        "id": t.id, "name": t.name, "description": t.description,
        "priority": t.priority, "time_slot": t.time_slot,
        "completed": t.completed, "archived": t.archived,
        "is_personal": t.is_personal, "is_selfcare": t.is_selfcare,
        "is_recurring": t.is_recurring, "is_dream": t.is_dream,
        "start_date": _d(t.start_date), "due_date": _d(t.due_date),
        "created_at": _d(t.created_at), "completed_at": _d(t.completed_at),
        "parent_id": t.parent_id, "subtasks": [], "size": t.size or "normal"
    }

@router.get("/tasks")
async def get_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task)
        .filter(Task.archived == False, Task.parent_id == None)
    )
    tasks = result.scalars().all()
    ids = [t.id for t in tasks]
    if ids:
        sub_res = await db.execute(
            select(Task).filter(Task.parent_id.in_(ids), Task.archived == False)
        )
        subs = sub_res.scalars().all()
        subs_by_parent = {}
        for s in subs:
            subs_by_parent.setdefault(s.parent_id, []).append(s)
        out = []
        for t in tasks:
            d = _task_to_dict(t)
            d["subtasks"] = [_task_to_dict(s) for s in subs_by_parent.get(t.id, [])]
            out.append(d)
        return out
    return [_task_to_dict(t) for t in tasks]

@router.post("/tasks")
async def add_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    name_lower = task_data.name.lower()
    is_p = task_data.is_personal
    is_dr = task_data.is_dream
    
    if task_data.parent_id:
        parent_stmt = select(Task).filter(Task.id == task_data.parent_id)
        parent_res = await db.execute(parent_stmt)
        parent = parent_res.scalar_one_or_none()
        if parent:
            is_p = parent.is_personal if task_data.is_personal is False else task_data.is_personal
            is_dr = parent.is_dream if task_data.is_dream is False else task_data.is_dream
    else:
        is_p = task_data.is_personal or "личн" in name_lower or "баланс" in name_lower
        
    is_sc = "для себ" in name_lower or "уход" in name_lower
    
    new_task = Task(
        name=task_data.name,
        description=task_data.description,
        priority=task_data.priority,
        time_slot=task_data.time_slot,
        parent_id=task_data.parent_id,
        is_personal=is_p,
        is_dream=is_dr,
        is_selfcare=is_sc,
        size=task_data.size,
        start_date=task_data.start_date,
        due_date=task_data.due_date
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    if task_data.parent_id:
        await _sync_parent(db, task_data.parent_id)
    return _task_to_dict(new_task)

@router.put("/tasks/{task_id}")
async def update_task(task_id: int, task_data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        update_data = task_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)
        await db.commit()
        await db.refresh(task)
        if task.parent_id:
            await _sync_parent(db, task.parent_id)
        return _task_to_dict(task)
    raise HTTPException(status_code=404, detail="Task not found")

async def _sync_parent(db: AsyncSession, parent_id: int):
    """Sync parent due_date from subtasks. Archive if all done."""
    subs_res = await db.execute(
        select(Task).filter(Task.parent_id == parent_id, Task.archived == False)
    )
    subs = subs_res.scalars().all()
    if not subs:
        return
    parent_res = await db.execute(select(Task).filter(Task.id == parent_id))
    parent = parent_res.scalar_one_or_none()
    if not parent:
        return
    
    active = [s for s in subs if not s.completed]
    if not active:
        parent.completed = True
        parent.completed_at = datetime.date.today()
    else:
        dates = [s.due_date for s in active if s.due_date]
        if dates:
            parent.due_date = min(dates)
    await db.commit()

@router.post("/tasks/auto-archive")
async def auto_archive_tasks(db: AsyncSession = Depends(get_db)):
    today = datetime.date.today()
    result = await db.execute(
        select(Task).filter(
            Task.completed == True,
            Task.archived == False,
            Task.completed_at < today
        )
    )
    tasks = result.scalars().all()
    for task in tasks:
        task.archived = True
    await db.commit()
    return {"archived_count": len(tasks)}

@router.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        task.completed = not task.completed
        if task.completed:
            task.completed_at = datetime.date.today()
        else:
            task.completed_at = None
        await db.commit()
        if task.parent_id:
            await _sync_parent(db, task.parent_id)
    return {"status": "ok"}

@router.post("/tasks/{task_id}/archive")
async def archive_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        task.archived = True
        await db.commit()
    return {"status": "ok"}

@router.get("/tasks/archived")
async def get_archived_tasks(q: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(Task).filter(Task.archived == True)
    if q:
        query = query.filter(Task.name.ilike(f"%{q}%"))
    result = await db.execute(query)
    return result.scalars().all()

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        await db.delete(task)
        await db.commit()
    return {"status": "ok"}

@router.post("/tasks/{task_id}/restore")
async def restore_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        task.archived = False
        await db.commit()
    return {"status": "ok"}

@router.post("/tasks/{task_id}/recurring")
async def toggle_recurring(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        task.is_recurring = not task.is_recurring
        await db.commit()
    return {"status": "ok"}

@router.post("/tasks/{task_id}/category")
async def update_task_category(task_id: int, is_personal: bool, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        task.is_personal = is_personal
        await db.commit()
    return {"status": "ok"}

@router.post("/tasks/{task_id}/dates")
async def update_task_dates(task_id: int, due_date: datetime.date, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        task.due_date = due_date
        await db.commit()
    return {"status": "ok"}

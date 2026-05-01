from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Task
import datetime
from typing import Optional

router = APIRouter()

@router.get("/tasks")
async def get_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.archived == False))
    return result.scalars().all()

@router.post("/tasks")
async def add_task(name: str, description: Optional[str] = None, start_date: Optional[datetime.date] = None, due_date: Optional[datetime.date] = None, is_dream: bool = False, is_personal: bool = False, db: AsyncSession = Depends(get_db)):
    is_p = is_personal or "личн" in name.lower() or "баланс" in name.lower()
    is_sc = "для себ" in name.lower() or "уход" in name.lower()
    new_task = Task(name=name, description=description, start_date=start_date, due_date=due_date, is_personal=is_p, is_selfcare=is_sc, is_dream=is_dream)
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

@router.put("/tasks/{task_id}")
async def update_task(task_id: int, name: Optional[str] = None, description: Optional[str] = None, start_date: Optional[datetime.date] = None, due_date: Optional[datetime.date] = None, is_dream: Optional[bool] = None, is_personal: Optional[bool] = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        if name is not None: task.name = name
        if description is not None: task.description = description
        if start_date is not None: task.start_date = start_date
        if due_date is not None: task.due_date = due_date
        if is_dream is not None: task.is_dream = is_dream
        if is_personal is not None: task.is_personal = is_personal
        await db.commit()
        return task
    raise HTTPException(status_code=404, detail="Task not found")

@router.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        task.completed = not task.completed
        await db.commit()
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
async def get_archived_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.archived == True))
    return result.scalars().all()

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

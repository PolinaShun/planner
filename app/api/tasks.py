from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.database import get_db
from app.models.models import Task
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
import datetime
from typing import Optional, List

router = APIRouter()

@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task)
        .filter(Task.archived == False, Task.parent_id == None)
        .options(selectinload(Task.subtasks))
    )
    return result.scalars().all()

@router.post("/tasks", response_model=TaskResponse)
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
        start_date=task_data.start_date,
        due_date=task_data.due_date
    )
    db.add(new_task)
    await db.commit()
    
    # ПЕРЕЗАГРУЗКА с подзадачами ОБЯЗАТЕЛЬНА
    final_stmt = select(Task).filter(Task.id == new_task.id).options(selectinload(Task.subtasks))
    final_res = await db.execute(final_stmt)
    return final_res.scalar_one()

@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, task_data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task)
        .filter(Task.id == task_id)
        .options(selectinload(Task.subtasks))
    )
    task = result.scalar_one_or_none()
    if task:
        update_data = task_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)
        await db.commit()
        
        refresh_stmt = select(Task).filter(Task.id == task.id).options(selectinload(Task.subtasks))
        refresh_res = await db.execute(refresh_stmt)
        return refresh_res.scalar_one()
    raise HTTPException(status_code=404, detail="Task not found")

@router.post("/tasks/auto-archive")
async def auto_archive_tasks(db: AsyncSession = Depends(get_db)):
    today = datetime.date.today()
    result = await db.execute(
        select(Task).filter(
            Task.completed == True,
            Task.archived == False,
            Task.created_at < today
        )
    )
    tasks = result.scalars().all()
    for task in tasks:
        task.archived = True
    await db.commit()
    return {"archived_count": len(tasks)}

@router.post("/tasks/{task_id}/toggle")
async def toggle_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Task)
        .filter(Task.id == task_id)
        .options(selectinload(Task.subtasks))
    )
    task = result.scalar_one_or_none()
    if task:
        task.completed = not task.completed
        if task.completed:
            task.completed_at = datetime.date.today()
        else:
            task.completed_at = None
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

@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if task:
        await db.delete(task)
        await db.commit()
    return {"status": "ok"}
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

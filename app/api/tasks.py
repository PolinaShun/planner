from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.database import get_db
from app.models.models import Task
from pydantic import BaseModel
from typing import List, Optional
import datetime
import re

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class Subtask(BaseModel):
    name: str
    completed: bool = False

class TaskCreate(BaseModel):
    name: str
    priority: str = "p1"
    time_slot: str = "Сегодня"
    is_personal: bool = False
    due_date: Optional[datetime.date] = None

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    priority: Optional[str] = None
    time_slot: Optional[str] = None
    completed: Optional[bool] = None
    archived: Optional[bool] = None
    is_personal: Optional[bool] = None
    due_date: Optional[datetime.date] = None
    subtasks: Optional[List[Subtask]] = None

@router.get("/")
async def get_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.archived == False))
    return result.scalars().all()

@router.post("/")
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_db)):
    # Simple NLP for due date: "до 27.04"
    name = task_data.name
    due_date = task_data.due_date
    
    date_match = re.search(r'до (\d{2})\.(\d{2})', name)
    if date_match:
        day, month = map(int, date_match.groups())
        year = datetime.date.today().year
        due_date = datetime.date(year, month, day)
        name = name.replace(date_match.group(0), '').strip()

    new_task = Task(
        name=name,
        priority=task_data.priority,
        time_slot=task_data.time_slot,
        is_personal=task_data.is_personal,
        due_date=due_date
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task

@router.patch("/{task_id}")
async def update_task(task_id: int, task_update: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_update.dict(exclude_unset=True)
    if 'subtasks' in update_data:
        update_data['subtasks'] = [s.dict() for s in update_data['subtasks']]
        
    for key, value in update_data.items():
        setattr(task, key, value)
    
    await db.commit()
    await db.refresh(task)
    return task

@router.post("/smart-archive")
async def smart_archive(db: AsyncSession = Depends(get_db)):
    # This will be implemented in a separate service to handle progress updates
    from app.services.archive_service import archive_completed_tasks
    stats = await archive_completed_tasks(db)
    return {"message": "Archive complete", "stats": stats}

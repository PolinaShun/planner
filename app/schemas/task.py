from pydantic import BaseModel
from datetime import date
from typing import Optional, List

class TaskBase(BaseModel):
    name: str
    description: Optional[str] = None
    priority: str = "p1"
    time_slot: str = "Сегодня"
    is_personal: bool = False
    is_dream: bool = False
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    parent_id: Optional[int] = None

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    time_slot: Optional[str] = None
    completed: Optional[bool] = None
    archived: Optional[bool] = None
    is_personal: Optional[bool] = None
    is_dream: Optional[bool] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    parent_id: Optional[int] = None

class TaskResponse(TaskBase):
    id: int
    completed: bool
    archived: bool
    is_selfcare: bool
    is_recurring: bool
    created_at: date
    subtasks: List['TaskResponse'] = []

    class Config:
        from_attributes = True

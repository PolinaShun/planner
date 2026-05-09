from pydantic import BaseModel
from datetime import date
from typing import Optional

class PostBase(BaseModel):
    title: str
    content: str
    platform: Optional[str] = "tg"
    status: Optional[str] = "draft"
    publish_date: Optional[date] = None

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    platform: Optional[str] = None
    status: Optional[str] = None
    publish_date: Optional[date] = None

class PostResponse(PostBase):
    id: int
    created_at: date

    class Config:
        from_attributes = True

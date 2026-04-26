from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
import datetime

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    priority = Column(String, default="p1") # p0, p1, p2
    time_slot = Column(String, default="Сегодня") # Сегодня, Завтра, На неделе, Архив
    completed = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    is_personal = Column(Boolean, default=False)
    due_date = Column(Date, nullable=True)
    subtasks = Column(JSON, default=list) # List of {"name": str, "completed": bool}
    created_at = Column(Date, default=datetime.date.today)

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    stages_total = Column(Integer, default=6)
    stages_done = Column(Integer, default=0)
    keywords = Column(JSON, default=list) # Keywords for auto-linking during smart archive

class BodyMetric(Base):
    __tablename__ = "body_metrics"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=datetime.date.today, unique=True)
    weight = Column(Float)
    waist = Column(Float)
    hips = Column(Float)

class Counter(Base):
    __tablename__ = "counters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False) # 'freud', 'nancy', 'tg', 'reels', etc.
    value = Column(Integer, default=0)
    target = Column(Integer, default=0)

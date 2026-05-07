from sqlalchemy import Column, Integer, String, Boolean, Float, JSON, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base
import datetime

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    priority = Column(String, default="p1")
    time_slot = Column(String, default="Сегодня")
    completed = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    is_personal = Column(Boolean, default=False)
    is_selfcare = Column(Boolean, default=False)
    is_recurring = Column(Boolean, default=False)
    is_dream = Column(Boolean, default=False)
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    created_at = Column(Date, default=datetime.date.today)
    completed_at = Column(Date, nullable=True)
    
    parent_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    subtasks = relationship("Task", backref="parent", remote_side=[id])

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    stages_total = Column(Integer, default=6)
    stages_done = Column(Integer, default=0)
    keywords = Column(JSON, default=list)

class Counter(Base):
    __tablename__ = "counters"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    value = Column(Integer, default=0)
    target = Column(Integer, default=10)

class BodyMetric(Base):
    __tablename__ = "body_metrics"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=datetime.date.today, unique=True)
    weight = Column(Float)
    waist = Column(Float)
    hips = Column(Float)
    chest = Column(Float, nullable=True)
    calories = Column(Integer, nullable=True)
    protein = Column(Integer, nullable=True)
    workout_history = Column(JSON, default=list) # List of 30 booleans

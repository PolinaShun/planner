from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(String, default="")
    is_active = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    start_date = Column(Date, nullable=True)
    target_days = Column(Integer, default=30)
    current_cycle = Column(Integer, default=1)
    # Циклический режим (пульс-терапия / интервальные трекеры)
    type = Column(String(10), default="daily")       # 'daily' | 'cycle'
    active_days = Column(Integer, default=7)          # дней приёма в курсе
    rest_days = Column(Integer, default=21)           # дней паузы
    total_cycles = Column(Integer, default=3)         # количество курсов
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan")

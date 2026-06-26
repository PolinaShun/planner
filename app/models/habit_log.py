from sqlalchemy import Column, Integer, Date, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base

class HabitLog(Base):
    __tablename__ = "habit_logs"

    id = Column(Integer, primary_key=True, index=True)
    habit_id = Column(Integer, ForeignKey("habits.id", ondelete="CASCADE"), nullable=False)
    cycle_number = Column(Integer, default=1)
    date = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    habit = relationship("Habit", back_populates="logs")

    __table_args__ = (
        UniqueConstraint('habit_id', 'date', 'cycle_number', name='_habit_date_cycle_uc'),
    )

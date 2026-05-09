import asyncio
import datetime
import calendar
from app.db.database import AsyncSessionLocal
from app.models.models import BodyMetric
from sqlalchemy import select, and_

MONTH_NAMES = ["", "ЯНВАРЬ", "ФЕВРАЛЬ", "МАРТ", "АПРЕЛЬ", "МАЙ", "ИЮНЬ", "ИЮЛЬ", "АВГУСТ", "СЕНТЯБРЬ", "ОКТЯБРЬ", "НОЯБРЬ", "ДЕКАБРЬ"]

async def debug_history():
    async with AsyncSessionLocal() as db:
        today = datetime.date.today()
        monthly_workout_stats = []
        for m_idx in range(1, 13):
            m_start = datetime.date(today.year, m_idx, 1)
            _, last_day = calendar.monthrange(today.year, m_idx)
            m_end = datetime.date(today.year, m_idx, last_day)
            
            m_res = await db.execute(select(BodyMetric).filter(and_(
                BodyMetric.date >= m_start,
                BodyMetric.date <= m_end
            )))
            m_metrics = m_res.scalars().all()
            
            if m_metrics:
                best_m = max(m_metrics, key=lambda x: sum(1 for d in x.workout_history if d))
                done = sum(1 for d in best_m.workout_history if d)
                total = len(best_m.workout_history)
                percent = int((done/total)*100) if total > 0 else 0
                monthly_workout_stats.append({"month": MONTH_NAMES[m_idx], "percent": percent})
            elif m_idx <= today.month:
                monthly_workout_stats.append({"month": MONTH_NAMES[m_idx], "percent": 0})
        
        print(f"DEBUG: monthly_workout_stats = {monthly_workout_stats}")

if __name__ == "__main__":
    asyncio.run(debug_history())

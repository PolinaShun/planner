import asyncio
import datetime
import calendar
from app.db.database import AsyncSessionLocal
from app.models.models import BodyMetric
from sqlalchemy import select

async def total_clean_may():
    today = datetime.date.today()
    _, days_in_month = calendar.monthrange(today.year, today.month)
    async with AsyncSessionLocal() as db:
        # Находим все записи за май
        res = await db.execute(select(BodyMetric).filter(BodyMetric.date >= datetime.date(today.year, today.month, 1)))
        metrics = res.scalars().all()
        for m in metrics:
            print(f"Cleaning record for {m.date}...")
            m.workout_history = [False] * days_in_month
        await db.commit()
        print("May is now absolutely clean.")

if __name__ == "__main__":
    asyncio.run(total_clean_may())

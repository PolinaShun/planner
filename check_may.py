import asyncio
import datetime
from app.db.database import AsyncSessionLocal
from app.models.models import BodyMetric
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        today = datetime.date.today()
        # Проверяем все записи с начала мая
        res = await db.execute(select(BodyMetric).filter(BodyMetric.date >= datetime.date(today.year, today.month, 1)))
        metrics = res.scalars().all()
        if not metrics:
            print("No records found for May.")
        for m in metrics:
            done = sum(1 for d in m.workout_history if d)
            print(f"Date: {m.date}, Done: {done}/{len(m.workout_history)}")

if __name__ == "__main__":
    asyncio.run(check())

import asyncio
from app.db.database import AsyncSessionLocal
from app.models.models import BodyMetric
from sqlalchemy import select
import datetime

async def get_april_data():
    async with AsyncSessionLocal() as db:
        # Ищем запись за конец апреля или самую свежую апрельскую
        res = await db.execute(select(BodyMetric).filter(
            BodyMetric.date >= datetime.date(2026, 4, 1),
            BodyMetric.date <= datetime.date(2026, 4, 30)
        ).order_by(BodyMetric.date.desc()))
        metrics = res.scalars().all()
        for m in metrics:
            done = sum(1 for d in m.workout_history if d)
            total = len(m.workout_history)
            print(f"Date: {m.date}, Done: {done}/{total}, History: {m.workout_history}")

if __name__ == "__main__":
    asyncio.run(get_april_data())

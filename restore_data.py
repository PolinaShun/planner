import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import AsyncSessionLocal, engine, Base
from app.models.models import Client, Counter, BodyMetric, Task
import datetime
from sqlalchemy import delete

async def restore():
    async with engine.begin() as conn:
        # Create tables
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Clear existing
        await db.execute(delete(Client))
        await db.execute(delete(Counter))
        await db.execute(delete(BodyMetric))
        
        # 2. Restore Study (Counters)
        db.add(Counter(name="Freud", value=1, target=35))
        db.add(Counter(name="Nancy", value=0, target=6))
        
        # 3. Restore Body Metrics
        history = [False] * 30
        history[0] = True
        db.add(BodyMetric(
            date=datetime.date.today(),
            weight=53.75,
            waist=61.0,
            hips=89.0,
            workout_history=history
        ))
        
        # 4. Restore Clients
        clients_data = [
            {"name": "Оля Соколова", "total": 6, "done": 2},
            {"name": "Т. Зарудный", "total": 42, "done": 0}
        ]
        for c in clients_data:
            db.add(Client(name=c["name"], stages_total=c["total"], stages_done=c["done"]))
            
        await db.commit()
        print("Данные успешно восстановлены в асинхронном режиме.")

if __name__ == "__main__":
    asyncio.run(restore())

import asyncio
from app.db.database import AsyncSessionLocal, engine, Base
from app.models.models import Task, Client, Counter, BodyMetric
import datetime

async def restore():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Задачи из скриншота
        tasks = [
            Task(name='Разобраться что делать с тг каналом', due_date=datetime.date(2026, 4, 27), time_slot='Сегодня'),
            Task(name='купить трусы', due_date=datetime.date(2026, 4, 29), is_personal=True, time_slot='Сегодня'),
            Task(name='снять видеовизитку для авито', time_slot='Сегодня'),
            Task(name='хочу сегодня выложить планировщика и выложить в Гид', due_date=datetime.date(2026, 5, 1), time_slot='Сегодня'),
        ]
        session.add_all(tasks)

        # 2. Клиенты (Юлия диплом - все 6 этапов)
        clients = [
            Client(name='Юлия — диплом', stages_total=6, stages_done=6, keywords=['юлия', 'диплом']),
        ]
        session.add_all(clients)

        # 3. Учеба (Фрейд и Нэнси)
        counters = [
            Counter(name='Freud', value=2, target=35),
            Counter(name='Нэнси (вебинары)', value=1, target=6),
            Counter(name='tg', value=0, target=10),
            Counter(name='reels', value=0, target=10),
            Counter(name='stories', value=0, target=10),
        ]
        session.add_all(counters)

        # 4. Тело (Вес, Талия и история тренировок по точкам на скрине)
        # На скрине отмечены дни: 1-6, 12-20, 23-25
        workout = [False] * 30
        for d in [1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 17, 18, 19, 20, 23, 24, 25]:
            workout[d-1] = True

        metric = BodyMetric(
            weight=53.75, 
            waist=61.0, 
            hips=89.0, 
            workout_history=workout,
            date=datetime.date.today()
        )
        session.add(metric)

        await session.commit()
        print("Данные успешно восстановлены из скриншота!")

if __name__ == "__main__":
    asyncio.run(restore())

import asyncio
from app.db.database import AsyncSessionLocal, engine, Base
from app.models.models import Task, Client, Counter, BodyMetric
import datetime

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Initial Tasks
        tasks = [
            Task(name='Зарина — КР "Психодиагностика"', priority='p0', time_slot='Сегодня'),
            Task(name='Зарина — КР "Психосоматика"', priority='p0', time_slot='Сегодня'),
            Task(name='Дарья — корректировки 1 главы', priority='p0', time_slot='Сегодня'),
            Task(name='Дарья — начать писать 2 главу', priority='p1', time_slot='Сегодня'),
            Task(name='Надежда — написать главу 1 и 2, отправить', priority='p0', time_slot='Завтра'),
            Task(name='Надежда — внести корректировки (травма)', priority='p0', time_slot='На неделе'),
            Task(name='Купить кроссовки', priority='p1', time_slot='На неделе', is_personal=True),
            Task(name='Купить мусорные мешки', priority='p2', time_slot='Сегодня', is_personal=True),
        ]
        session.add_all(tasks)

        # Clients
        clients = [
            Client(name='Юлия — диплом', stages_total=6, stages_done=5, keywords=['юлия', 'диплом']),
            Client(name='Надежда — ВКР', stages_total=6, stages_done=1, keywords=['надежда', 'вкр']),
            Client(name='Дарья — диплом', stages_total=5, stages_done=4, keywords=['дарья']),
            Client(name='Зарина — 9 эссе', stages_total=9, stages_done=7, keywords=['зарина', 'эссе']),
        ]
        session.add_all(clients)

        # Counters
        counters = [
            Counter(name='freud', value=1, target=35),
            Counter(name='nancy', value=0, target=6),
            Counter(name='tg', value=0, target=10),
            Counter(name='reels', value=0, target=10),
            Counter(name='stories', value=0, target=10),
            Counter(name='threads', value=0, target=10),
            Counter(name='tax', value=2, target=6),
        ]
        session.add_all(counters)

        # Initial Metrics
        metric = BodyMetric(weight=53.75, waist=67, hips=93)
        session.add(metric)

        await session.commit()

if __name__ == "__main__":
    asyncio.run(seed())

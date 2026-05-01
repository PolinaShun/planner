import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import Base, engine, AsyncSessionLocal
import datetime

# This is needed for pytest-asyncio to know which loop to use
@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_create_task_with_nlp():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test basic creation
        response = await ac.post("/api/tasks/", json={"name": "Обычная задача"})
        assert response.status_code == 200
        assert response.json()["name"] == "Обычная задача"
        
        # Test NLP date
        response = await ac.post("/api/tasks/", json={"name": "до 30.04 Сдать проект"})
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Сдать проект"
        assert data["due_date"] == f"{datetime.date.today().year}-04-30"

@pytest.mark.asyncio
async def test_smart_archive():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a client and counter manually in DB
        async with AsyncSessionLocal() as session:
            from app.models.models import Client, Counter
            client = Client(name="Зарина", keywords=["зарина"], stages_total=5, stages_done=0)
            counter = Counter(name="freud", value=0, target=10)
            session.add_all([client, counter])
            await session.commit()

        # 2. Create and complete a task for the client
        resp = await ac.post("/api/tasks/", json={"name": "Зарина — КР"})
        task_id = resp.json()["id"]
        await ac.patch(f"/api/tasks/{task_id}", json={"completed": True})

        # 3. Run smart archive
        response = await ac.post("/api/tasks/smart-archive")
        assert response.status_code == 200
        
        # 4. Verify results
        progress = await ac.get("/api/stats/progress")
        data = progress.json()
        # Find client Зарина
        zarina = next(c for c in data["clients"] if c["name"] == "Зарина")
        assert zarina["stages_done"] == 1

import asyncio
from app.db.database import engine, Base
import os

async def init_db():
    print("Initializing database...")
    async with engine.begin() as conn:
        # Это создаст все таблицы, если их нет
        await conn.run_sync(Base.metadata.create_all)
    print("Database structure created successfully (planner.db)")

if __name__ == "__main__":
    asyncio.run(init_db())

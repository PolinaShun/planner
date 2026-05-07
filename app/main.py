from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import engine, Base, get_db
from app.models import models
import os
import datetime
import shutil

from app.api import tasks, stats

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Senior Planner Polina")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files and templates
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include routers with explicit prefixes for consistency
app.include_router(tasks.router, prefix="/api")
app.include_router(stats.router, prefix="/api")

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Automated daily backup
    if os.path.exists("planner.db"):
        if not os.path.exists("backups"):
            os.makedirs("backups")
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        shutil.copy("planner.db", f"backups/planner_{ts}.db")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/export")
async def export_db():
    # Ищем БД в корне проекта (на уровень выше от папки app)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "planner.db")
    
    if os.path.exists(db_path):
        return FileResponse(db_path, filename=f"planner_export_{datetime.date.today()}.db", media_type="application/x-sqlite3")
    
    # Запасной вариант - текущая рабочая директория
    if os.path.exists("planner.db"):
        return FileResponse("planner.db", filename=f"planner_export_{datetime.date.today()}.db", media_type="application/x-sqlite3")
        
    return {"error": f"Database file not found at {db_path}"}

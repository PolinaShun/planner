from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import engine, Base, get_db
from app.models import models
import os
import datetime
import shutil

from app.api import tasks, stats, posts, habits
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Senior Planner Polina")

API_TOKEN = os.getenv("API_TOKEN", "")

LOGIN_PAGE = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Вход</title>
<style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;background:#faf6f1;}
form{display:flex;flex-direction:column;gap:12px;padding:32px;background:#fff;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.1);}
input{padding:12px 16px;border:1px solid #e0d8cc;border-radius:12px;font-size:16px;outline:none;}
button{background:#c4826b;color:#fff;border:none;padding:14px;border-radius:12px;font-size:16px;cursor:pointer;}</style></head>
<body><form method="GET"><h2>Планировщик Полины</h2><input type="password" name="token" placeholder="Токен" autofocus><button>Войти</button></form></body></html>"""

@app.middleware("http")
async def check_auth(request: Request, call_next):
    if request.url.path.startswith("/static") or request.url.path == "/favicon.ico":
        return await call_next(request)
    # Only protect the main page, not API
    if not API_TOKEN:
        return await call_next(request)
    token = request.cookies.get("planner_token", "")
    if not token:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = request.query_params.get("token", "")
    if token == API_TOKEN:
        response = await call_next(request)
        if not request.cookies.get("planner_token"):
            response.set_cookie("planner_token", token, max_age=86400*30)
        return response
    # No valid token
    if request.url.path.startswith("/api"):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    return HTMLResponse(content=LOGIN_PAGE, status_code=200)

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
app.include_router(posts.router, prefix="/api")
app.include_router(habits.router)

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
    template = templates.get_template("index.html")
    content = template.render({"request": request})
    return HTMLResponse(content=content, headers={"Cache-Control": "no-cache", "Pragma": "no-cache", "Expires": "0"})

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

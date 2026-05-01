@echo off
title Senior Planner Polina
echo Starting Senior Planner...

:: Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python from python.org
    pause
    exit /b
)

:: Установка зависимостей если нужно
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

:: Запуск сервера
echo Server starting at http://localhost:8000
python -m uvicorn app.main:app --port 8000 --host 127.0.0.1
pause

from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, update
from app.db.database import get_db
from app.models.habit import Habit
from app.models.habit_log import HabitLog
from datetime import date, timedelta
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from typing import List

router = APIRouter(prefix="/api/habits", tags=["habits"])

class HabitToggle(BaseModel):
    habit_id: int
    date: date

class HabitCreate(BaseModel):
    title: str
    target_days: int = 30

def compute_next_cycle_start(habit: Habit, today: date) -> date:
    target_days = habit.target_days or 30
    old_start = habit.start_date or today
    scheduled = old_start + timedelta(days=target_days)
    return scheduled if scheduled <= today else today

def build_habit_cycle_grid(habit: Habit, today: date) -> dict:
    target_days = habit.target_days or 30
    start = habit.start_date or today
    dates = [start + timedelta(days=i) for i in range(target_days)]
    return {"start": start, "dates": dates, "start_weekday": start.weekday(), "target_days": target_days}

@router.get("/")
async def get_habits(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Habit).where(Habit.is_active == True, Habit.is_archived == False)
    )
    return result.scalars().all()

@router.get("/dashboard")
async def get_habits_dashboard(db: AsyncSession = Depends(get_db)):
    """Возвращает JSON для дашборда: привычки + сетки + сегодня."""
    today = date.today()
    result = await db.execute(
        select(Habit).where(Habit.is_active == True, Habit.is_archived == False)
    )
    habits = result.scalars().all()
    out = []
    for h in habits:
        grid = build_habit_cycle_grid(h, today)
        logs_res = await db.execute(
            select(HabitLog).where(
                HabitLog.habit_id == h.id,
                HabitLog.cycle_number == h.current_cycle
            )
        )
        marked = {log.date.isoformat() for log in logs_res.scalars().all()}
        out.append({
            "id": h.id, "title": h.title, "target_days": h.target_days,
            "current_cycle": h.current_cycle, "start_date": str(h.start_date) if h.start_date else None,
            "grid": {"dates": [d.isoformat() for d in grid["dates"]], "start_weekday": grid["start_weekday"]},
            "marked_dates": list(marked), "progress": len(marked)
        })
    return out

@router.post("/create")
async def create_habit(data: HabitCreate, db: AsyncSession = Depends(get_db)):
    new_habit = Habit(
        title=data.title,
        start_date=date.today(),
        target_days=data.target_days or 30
    )
    db.add(new_habit)
    await db.commit()
    await db.refresh(new_habit)
    return {"id": new_habit.id, "title": new_habit.title}

@router.post("/toggle")
async def toggle_habit(data: HabitToggle, db: AsyncSession = Depends(get_db)):
    habit_res = await db.execute(select(Habit).where(Habit.id == data.habit_id))
    habit = habit_res.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    result = await db.execute(
        select(HabitLog).where(
            and_(
                HabitLog.habit_id == data.habit_id,
                HabitLog.date == data.date,
                HabitLog.cycle_number == habit.current_cycle
            )
        )
    )
    existing_log = result.scalar_one_or_none()
    if existing_log:
        await db.delete(existing_log)
        action = "removed"
    else:
        new_log = HabitLog(habit_id=data.habit_id, date=data.date, cycle_number=habit.current_cycle)
        db.add(new_log)
        action = "added"
    await db.commit()
    return {"status": "success", "action": action}

@router.delete("/{habit_id}")
async def archive_habit(habit_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Habit).where(Habit.id == habit_id))
    habit = result.scalar_one_or_none()
    if habit:
        habit.is_archived = True
        await db.commit()
    return {"status": "ok"}

@router.post("/{habit_id}/next-cycle")
async def restart_habit_cycle(habit_id: int, db: AsyncSession = Depends(get_db)):
    today = date.today()
    result = await db.execute(select(Habit).where(Habit.id == habit_id))
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    habit.current_cycle += 1
    habit.start_date = compute_next_cycle_start(habit, today)
    await db.commit()
    return {"status": "ok"}

def compute_cycle_start_dates(habit: Habit, logs_by_cycle: dict) -> dict:
    target_days = habit.target_days or 30
    starts = {}
    next_start = habit.start_date or date.today()
    starts[habit.current_cycle] = next_start
    for cycle_num in range(habit.current_cycle - 1, 0, -1):
        candidate = next_start - timedelta(days=target_days)
        marked = logs_by_cycle.get(cycle_num, [])
        if marked:
            mark_min = min(marked)
            window_end = candidate + timedelta(days=target_days - 1)
            starts[cycle_num] = mark_min if (mark_min < candidate or max(marked) > window_end) else candidate
        else:
            starts[cycle_num] = candidate
        next_start = starts[cycle_num]
    return starts

def build_habit_history_cycles(habit: Habit, logs: list, today: date) -> list:
    by_cycle = defaultdict(list)
    for log in logs:
        by_cycle[log.cycle_number].append(log.date)
    target_days = habit.target_days or 30
    cycle_starts = compute_cycle_start_dates(habit, by_cycle)
    cycles = []
    for cycle_num in range(habit.current_cycle, 0, -1):
        marked_dates = sorted(set(by_cycle.get(cycle_num, [])))
        is_current = cycle_num == habit.current_cycle
        marked_iso = {d.isoformat() for d in marked_dates}
        if is_current:
            grid = build_habit_cycle_grid(habit, today)
            dates_list = grid["dates"]
            start_weekday = grid["start_weekday"]
        else:
            start = cycle_starts[cycle_num]
            dates_list = [start + timedelta(days=i) for i in range(target_days)]
            start_weekday = start.weekday()
        cycles.append({
            "cycle_number": cycle_num, "is_current": is_current,
            "empty": not marked_dates, "dates": [d.isoformat() for d in dates_list],
            "logs": list(marked_iso), "progress": len(marked_iso),
            "start_weekday": start_weekday, "target_days": target_days,
        })
    return cycles

@router.get("/{habit_id}/history")
async def habit_history(habit_id: int, db: AsyncSession = Depends(get_db)):
    today = date.today()
    result = await db.execute(select(Habit).where(Habit.id == habit_id))
    habit = result.scalar_one_or_none()
    if not habit:
        raise HTTPException(status_code=404)
    logs_result = await db.execute(
        select(HabitLog).where(HabitLog.habit_id == habit_id).order_by(HabitLog.cycle_number, HabitLog.date)
    )
    logs = list(logs_result.scalars().all())
    cycles = build_habit_history_cycles(habit, logs, today)
    return {"title": habit.title, "cycles": cycles, "total_marks": len(logs)}

from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, update
from app.db.database import get_db
from app.models.habit import Habit
from app.models.habit_log import HabitLog
from datetime import date, timedelta
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import HTMLResponse
from typing import List

router = APIRouter(prefix="/api/habits", tags=["habits"])

class HabitToggle(BaseModel):
    habit_id: int
    date: date

class HabitCreate(BaseModel):
    title: str
    target_days: int = 30
    start_date: Optional[date] = None
    type: Optional[str] = "daily"       # 'daily' | 'cycle'
    active_days: Optional[int] = 7
    rest_days: Optional[int] = 21
    total_cycles: Optional[int] = 3

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

def is_cycle(habit: Habit) -> bool:
    return getattr(habit, "type", None) == "cycle"

def cycle_info(habit: Habit, d: date) -> dict:
    """Для циклического трекера возвращает фазу по конкретной дате d."""
    if not is_cycle(habit):
        return None
    start = habit.start_date or d
    active = habit.active_days or 7
    rest = habit.rest_days or 21
    total = habit.total_cycles or 3
    period = active + rest
    offset = (d - start).days
    if offset < 0:
        return {"active": False, "course": 1, "day": 0, "rest_left": None, "before": True, "after": False}
    cycle_idx = offset // period
    pos = offset % period
    course = cycle_idx + 1
    if cycle_idx >= total:
        return {"active": False, "course": total, "day": 0, "rest_left": None, "before": False, "after": True}
    if pos < active:
        return {"active": True, "course": course, "day": pos + 1, "rest_left": None, "before": False, "after": False}
    rest_elapsed = pos - active + 1
    rest_left = rest - (rest_elapsed - 1)
    return {"active": False, "course": course, "day": 0, "rest_left": rest_left, "before": False, "after": False}

def cycle_active_dates(habit: Habit, start_span: date, end_span: date) -> set:
    """Все активные даты (приёма) в диапазоне [start_span, end_span] включительно."""
    if not is_cycle(habit):
        return set()
    hstart = habit.start_date
    active = habit.active_days or 7
    rest = habit.rest_days or 21
    total = habit.total_cycles or 3
    period = active + rest
    out = set()
    if not hstart:
        return out
    # Проверяем начало каждого курса, пока оно в пределах диапазона
    for c in range(total):
        cstart = hstart + timedelta(days=c * period)
        cend = cstart + timedelta(days=active - 1)
        # пересечение [cstart, cend] с [start_span, end_span]
        lo = max(cstart, start_span)
        hi = min(cend, end_span)
        if lo <= hi:
            d = lo
            while d <= hi:
                out.add(d)
                d += timedelta(days=1)
    return out

def cycle_current_phase(habit: Habit, today: date) -> dict:
    """Фаза текущего дня + прогресс по активным дням текущего курса."""
    if not is_cycle(habit):
        return {"is_cycle": False}
    info = cycle_info(habit, today)
    active = habit.active_days or 7
    rest = habit.rest_days or 21
    total = habit.total_cycles or 3
    period = active + rest
    course = info["course"] or 1
    cstart = (habit.start_date or today) + timedelta(days=(course - 1) * period)
    cactive = [cstart + timedelta(days=i) for i in range(active)]
    # Дата начала следующего (ещё не начатого) курса
    next_course_start = None
    next_course_num = None
    if course < total:
        next_course_start = (habit.start_date or today) + timedelta(days=course * period)
        next_course_num = course + 1
    return {
        "is_cycle": True,
        "active": info["active"],
        "before": info["before"],
        "after": info["after"],
        "course": course,
        "total_courses": total,
        "day": info["day"],
        "active_days": active,
        "rest_left": info["rest_left"],
        "course_active_start": cstart.isoformat(),
        "course_active_dates": [d.isoformat() for d in cactive],
        "next_course_start": next_course_start.isoformat() if next_course_start else None,
        "next_course_num": next_course_num,
    }

def cycle_total_progress(habit: Habit, marked: set) -> tuple:
    """Общий прогресс всего лечения: (сделано активных дней, всего активных дней)."""
    if not is_cycle(habit):
        return (0, 0)
    start = habit.start_date
    active = habit.active_days or 7
    rest = habit.rest_days or 21
    total = habit.total_cycles or 3
    period = active + rest
    if not start:
        return (0, 0)
    done = 0
    total_days = 0
    for c in range(total):
        cstart = start + timedelta(days=c * period)
        for i in range(active):
            d = cstart + timedelta(days=i)
            total_days += 1
            if d.isoformat() in marked:
                done += 1
    return (done, total_days)

@router.get("/")
async def get_habits(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Habit).where(Habit.is_active == True, Habit.is_archived == False)
    )
    return result.scalars().all()

@router.get("/dashboard")
async def get_habits_dashboard(db: AsyncSession = Depends(get_db)):
    """Возвращает JSON для дашборда: привычки + сетки по ТЕКУЩЕМУ КАЛЕНДАРНОМУ МЕСЯЦУ + отметки за месяц."""
    today = date.today()
    import calendar
    month_start = date(today.year, today.month, 1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    month_days = [month_start + timedelta(days=i) for i in range(last_day)]

    result = await db.execute(
        select(Habit).where(Habit.is_active == True, Habit.is_archived == False)
    )
    habits = result.scalars().all()
    out = []
    for h in habits:
        # Все отметки этой привычки, попадающие в текущий календарный месяц (из любого цикла)
        logs_res = await db.execute(
            select(HabitLog).where(
                HabitLog.habit_id == h.id,
                HabitLog.date >= month_start
            )
        )
        logs = logs_res.scalars().all()
        marked = {log.date.isoformat() for log in logs}
        item = {
            "id": h.id, "title": h.title, "target_days": last_day,
            "current_cycle": h.current_cycle, "start_date": str(h.start_date) if h.start_date else None,
            "grid": {"dates": [d.isoformat() for d in month_days], "start_weekday": month_start.weekday()},
            "marked_dates": list(marked), "progress": len(marked),
            "type": getattr(h, "type", "daily"),
        }
        if is_cycle(h):
            active_dates = cycle_active_dates(h, month_start, month_days[-1])
            active_iso = sorted(d.isoformat() for d in active_dates)
            phase = cycle_current_phase(h, today)
            # Прогресс по активным дням ТЕКУЩЕГО курса
            course_active = set(phase.get("course_active_dates", []))
            course_done = len(course_active & marked)
            phase["course_done"] = course_done
            phase["course_total"] = phase.get("active_days", 7)
            td, tt = cycle_total_progress(h, marked)
            phase["total_done"] = td
            phase["total_total"] = tt
            item["cycle"] = {
                "active_days": getattr(h, "active_days", 7) or 7,
                "rest_days": getattr(h, "rest_days", 21) or 21,
                "total_cycles": getattr(h, "total_cycles", 3) or 3,
                "active_dates": active_iso,
                "phase": phase,
            }
        out.append(item)
    return out

@router.post("/create")
async def create_habit(data: HabitCreate, db: AsyncSession = Depends(get_db)):
    new_habit = Habit(
        title=data.title,
        start_date=data.start_date or date.today(),
        target_days=data.target_days or 30,
        type=data.type or "daily",
        active_days=data.active_days or 7,
        rest_days=data.rest_days or 21,
        total_cycles=data.total_cycles or 3
    )
    db.add(new_habit)
    await db.commit()
    await db.refresh(new_habit)
    return {"id": new_habit.id, "title": new_habit.title, "type": new_habit.type}

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

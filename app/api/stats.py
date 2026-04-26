from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.models import Client, Counter, BodyMetric
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/progress")
async def get_progress(db: AsyncSession = Depends(get_db)):
    clients = await db.execute(select(Client))
    counters = await db.execute(select(Counter))
    metrics = await db.execute(select(BodyMetric).order_by(BodyMetric.date.desc()).limit(1))
    
    return {
        "clients": clients.scalars().all(),
        "counters": {c.name: {"value": c.value, "target": c.target} for c in counters.scalars().all()},
        "metrics": metrics.scalar_one_or_none()
    }

@router.post("/metrics")
async def update_metrics(weight: float, waist: float, hips: float, db: AsyncSession = Depends(get_db)):
    metric = BodyMetric(weight=weight, waist=waist, hips=hips)
    db.add(metric)
    await db.commit()
    return metric

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Task, Client, Counter
import re

async def archive_completed_tasks(db: AsyncSession):
    # Find all completed but not archived tasks
    result = await db.execute(select(Task).where(Task.completed == True, Task.archived == False))
    tasks = result.scalars().all()
    
    if not tasks:
        return {"archived_count": 0}

    # Load all clients and counters for matching
    clients_result = await db.execute(select(Client))
    clients = clients_result.scalars().all()
    
    counters_result = await db.execute(select(Counter))
    counters = {c.name: c for c in counters_result.scalars().all()}
    
    stats = {
        "archived_count": len(tasks),
        "client_updates": 0,
        "counter_updates": 0
    }

    for task in tasks:
        name_lower = task.name.lower()
        
        # 1. Match against clients
        for client in clients:
            match = False
            for kw in client.keywords:
                if kw.lower() in name_lower:
                    match = True
                    break
            
            if match:
                if client.stages_done < client.stages_total:
                    client.stages_done += 1
                    stats["client_updates"] += 1
                break # Move to next task after first client match

        # 2. Match against counters (Study/Content)
        if 'фрейд' in name_lower or 'лекция' in name_lower:
            if 'freud' in counters:
                counters['freud'].value += 1
                stats["counter_updates"] += 1
        
        if 'пост' in name_lower or 'тг' in name_lower:
            if 'tg' in counters:
                counters['tg'].value += 1
                stats["counter_updates"] += 1
                
        if 'рилс' in name_lower:
            if 'reels' in counters:
                counters['reels'].value += 1
                stats["counter_updates"] += 1

        # Mark as archived
        task.archived = True

    await db.commit()
    return stats

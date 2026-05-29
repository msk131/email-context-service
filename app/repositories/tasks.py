from typing import Optional
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tasks import BackgroundTask, TaskStatus


async def create_task(session: AsyncSession, task_type: str, payload: dict) -> BackgroundTask:
    task = BackgroundTask(task_type=task_type, payload=payload, status=TaskStatus.pending, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def get_task(session: AsyncSession, task_id: int) -> Optional[BackgroundTask]:
    q = select(BackgroundTask).where(BackgroundTask.id == task_id)
    res = await session.execute(q)
    return res.scalars().first()


async def fetch_pending(session: AsyncSession, limit: int = 10):
    q = select(BackgroundTask).where(BackgroundTask.status == TaskStatus.pending).limit(limit)
    res = await session.execute(q)
    return res.scalars().all()


async def mark_running(session: AsyncSession, task_id: int):
    await session.execute(update(BackgroundTask).where(BackgroundTask.id == task_id).values(status=TaskStatus.running, updated_at=datetime.utcnow()))
    await session.commit()


async def mark_succeeded(session: AsyncSession, task_id: int, result: dict):
    await session.execute(update(BackgroundTask).where(BackgroundTask.id == task_id).values(status=TaskStatus.succeeded, result=result, updated_at=datetime.utcnow()))
    await session.commit()


async def mark_failed(session: AsyncSession, task_id: int, error: str):
    await session.execute(update(BackgroundTask).where(BackgroundTask.id == task_id).values(status=TaskStatus.failed, error=error, updated_at=datetime.utcnow()))
    await session.commit()

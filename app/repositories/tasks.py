from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time import utc_now
from app.models.tasks import BackgroundTask, TaskStatus, TASK_TTL_SUCCEEDED, TASK_TTL_FAILED


async def create_task(session: AsyncSession, task_type: str, payload: dict) -> BackgroundTask:
    now = utc_now()
    task = BackgroundTask(
        task_type=task_type,
        payload=payload,
        status=TaskStatus.pending,
        created_at=now,
        updated_at=now,
    )
    session.add(task)
    await session.flush()
    return task


async def get_task(session: AsyncSession, task_id: UUID) -> Optional[BackgroundTask]:
    q = select(BackgroundTask).where(BackgroundTask.id == task_id)
    res = await session.execute(q)
    return res.scalars().first()


async def fetch_pending(session: AsyncSession, limit: int = 10):
    q = select(BackgroundTask).where(BackgroundTask.status == TaskStatus.pending).limit(limit)
    res = await session.execute(q)
    return res.scalars().all()


async def mark_running(session: AsyncSession, task_id: UUID):
    await session.execute(update(BackgroundTask).where(BackgroundTask.id == task_id).values(status=TaskStatus.running, updated_at=utc_now()))
    await session.flush()


async def claim_pending_task(session: AsyncSession, task_id: UUID) -> Optional[BackgroundTask]:
    """Atomically move a pending task to running and return it when claimed."""
    result = await session.execute(
        update(BackgroundTask)
        .where(
            BackgroundTask.id == task_id,
            BackgroundTask.status == TaskStatus.pending,
        )
        .values(status=TaskStatus.running, updated_at=utc_now())
    )
    await session.commit()
    if result.rowcount != 1:
        return None
    return await get_task(session, task_id)


async def mark_succeeded(session: AsyncSession, task_id: UUID, result: dict):
    now = utc_now()
    expires_at = now + TASK_TTL_SUCCEEDED
    await session.execute(update(BackgroundTask).where(BackgroundTask.id == task_id).values(
        status=TaskStatus.succeeded, 
        result=result, 
        updated_at=now,
        completed_at=now,
        expires_at=expires_at
    ))
    await session.flush()


async def mark_failed(session: AsyncSession, task_id: UUID, error: str):
    now = utc_now()
    expires_at = now + TASK_TTL_FAILED
    await session.execute(update(BackgroundTask).where(BackgroundTask.id == task_id).values(
        status=TaskStatus.failed, 
        error=error, 
        updated_at=now,
        completed_at=now,
        expires_at=expires_at
    ))
    await session.flush()


async def cleanup_expired_tasks(session: AsyncSession, limit: int = 10000) -> int:
    """
    Delete expired tasks in batches to avoid locking issues.
    Returns the number of deleted tasks.
    """
    now = utc_now()
    expired_ids_result = await session.execute(
        select(BackgroundTask.id)
        .where(
            and_(
                BackgroundTask.expires_at.isnot(None),
                BackgroundTask.expires_at < now,
                BackgroundTask.status.in_([TaskStatus.succeeded, TaskStatus.failed]),
            )
        )
        .limit(limit)
    )
    expired_ids = expired_ids_result.scalars().all()
    if not expired_ids:
        return 0

    result = await session.execute(
        delete(BackgroundTask).where(BackgroundTask.id.in_(expired_ids))
    )
    await session.flush()
    return result.rowcount

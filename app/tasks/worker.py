import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.core.logging_config import get_logger, request_id_ctx_var
from app.repositories import tasks as task_repo
from app.models.background_task import BackgroundTask
from app.services.summaries import refresh_client_summary

logger = get_logger("tasks.worker")

# Cleanup runs every 3600 seconds (1 hour)
CLEANUP_INTERVAL_SECONDS = 3600
CLEANUP_BATCH_SIZE = 10000
MAX_CONCURRENT_TASKS = 5


def _task_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "client_id": int(payload.get("client_id")),
        "start_date": _parse_datetime(payload.get("start_date")),
        "end_date": _parse_datetime(payload.get("end_date")),
        "force": bool(payload.get("force", False)),
    }


async def _process_task(session: AsyncSession, task: BackgroundTask) -> None:
    try:
        logger.info("Starting task task_id=%s task_type=%s", task.id, task.task_type)
        payload = task.payload or {}
        task_args = _task_payload(payload)
        logger.info(
            "Refreshing summary from task task_id=%s client_id=%s force=%s",
            task.id,
            task_args["client_id"],
            task_args["force"],
        )

        result = await refresh_client_summary(
            session,
            **task_args,
        )
        await task_repo.mark_succeeded(session, task.id, result.model_dump(mode="json"))
        await session.commit()
        logger.info(
            "Task succeeded task_id=%s client_id=%s", task.id, task_args["client_id"]
        )
    except Exception as exc:
        await task_repo.mark_failed(session, task.id, error_code="TASK_EXECUTION_FAILED")
        await session.commit()
        logger.error("Task failed task_id=%s error=%s", task.id, exc, exc_info=True)


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


async def process_task_by_id(task_id: UUID, request_id: str | None = None) -> None:
    token = request_id_ctx_var.set(request_id) if request_id else None
    try:
        async with async_session() as session:
            task = await task_repo.claim_pending_task(session, task_id)
            if task is None:
                logger.info("Task not pending or not found task_id=%s", task_id)
                return
            await _process_task(session, task)
    finally:
        if token is not None:
            request_id_ctx_var.reset(token)


async def cleanup_expired_tasks_periodically() -> None:
    """Run cleanup every CLEANUP_INTERVAL_SECONDS to prevent unbounded table growth."""
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            async with async_session() as session:
                deleted_count = await task_repo.cleanup_expired_tasks(
                    session, limit=CLEANUP_BATCH_SIZE
                )
                await session.commit()
                if deleted_count > 0:
                    logger.info("Cleanup: deleted %d expired tasks", deleted_count)
        except Exception as e:
            logger.error("Cleanup task failed: %s", e, exc_info=True)


async def worker_loop(poll_interval: float = 2.0) -> None:
    # Start cleanup task as a background coroutine
    asyncio.create_task(cleanup_expired_tasks_periodically())

    while True:
        async with async_session() as session:
            pending = await task_repo.fetch_pending(session, limit=MAX_CONCURRENT_TASKS)
            task_ids = [task.id for task in pending]
        if task_ids:
            results = await asyncio.gather(
                *(process_task_by_id(task_id) for task_id in task_ids),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    logger.error(
                        "Worker task processing failed: %s",
                        result,
                        exc_info=(type(result), result, result.__traceback__),
                    )
        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(worker_loop())

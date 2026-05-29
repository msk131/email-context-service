import asyncio
import traceback

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session
from app.repositories import tasks as task_repo
from app.services.summaries import refresh_client_summary


async def _process_task(session: AsyncSession, task):
    try:
        await task_repo.mark_running(session, task.id)
        payload = task.payload or {}
        # Expecting payload: { "client_id": int, "start_date": str?, "end_date": str?, "force": bool }
        client_id = int(payload.get("client_id"))
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        force = bool(payload.get("force", False))

        result = await refresh_client_summary(session, client_id=client_id, start_date=start_date, end_date=end_date, force=force)
        # store simplified result
        await task_repo.mark_succeeded(session, task.id, result.model_dump())
    except Exception as exc:
        tb = traceback.format_exc()
        await task_repo.mark_failed(session, task.id, error=str(exc) + "\n" + tb)


async def worker_loop(poll_interval: float = 2.0):
    while True:
        async with async_session() as session:
            pending = await task_repo.fetch_pending(session, limit=5)
            for task in pending:
                # spawn subtasks to avoid blocking polling
                asyncio.create_task(_process_task(session, task))
        await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(worker_loop())

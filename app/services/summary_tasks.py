"""Summary task submission services."""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role
from app.models.users import User
from app.repositories import tasks as task_repo
from app.repositories.summaries import load_client
from app.schemas.summaries import SummaryRefreshTaskResponse
from app.services.clients import authorize_client_for_user
from app.utils import normalize_date_range


async def enqueue_summary_refresh_task(
    session: AsyncSession,
    *,
    current_user: User,
    client_id: int,
    force: bool = False,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> SummaryRefreshTaskResponse:
    """Authorize and enqueue a summary refresh task."""
    client = await load_client(session, client_id)
    await authorize_client_for_user(current_user, client, Role(current_user.role.value))
    try:
        normalize_date_range(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    task = await task_repo.create_task(
        session,
        task_type="summarize_client",
        payload={
            "client_id": client_id,
            "force": force,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    )
    await session.commit()
    await session.refresh(task)
    return SummaryRefreshTaskResponse(task_id=task.id, status=task.status.value)

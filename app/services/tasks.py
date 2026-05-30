"""Task application services."""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import EntityNotFoundError
from app.common.schemas import Role
from app.models.auth import Accountant
from app.models.clients import Client
from app.repositories import tasks as task_repo
from app.schemas.tasks import TaskCreateRequest, TaskCreateResponse, TaskStatusResponse
from app.services.clients import authorize_client_for_user


def _task_status_value(status: Any) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _serialize_task_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.isoformat() if hasattr(value, "isoformat") else value
        for key, value in payload.items()
    }


def _public_task_error(error: str | None) -> str | None:
    """Return a client-safe failure message without tracebacks or internals."""
    if not error:
        return None
    return "Task failed. Check server logs with the task_id for details."


async def authorize_task_payload(
    session: AsyncSession,
    current_user: Accountant,
    payload: dict[str, Any],
    *,
    require_client_id: bool = False,
) -> None:
    """Authorize access to the client referenced by a task payload."""
    client_id = payload.get("client_id")
    if client_id is None:
        if require_client_id:
            raise ValueError("payload.client_id is required")
        return

    try:
        resolved_client_id = int(client_id)
    except (TypeError, ValueError) as exc:
        raise TypeError("payload.client_id must be an integer") from exc

    client = await session.get(Client, resolved_client_id)
    if not client:
        raise EntityNotFoundError("Client", client_id)
    await authorize_client_for_user(current_user, client, Role(current_user.role.value))


async def enqueue_task_service(
    session: AsyncSession,
    *,
    current_user: Accountant,
    request: TaskCreateRequest,
) -> TaskCreateResponse:
    """Validate, authorize, and enqueue a background task."""
    payload = request.payload.model_dump(exclude_none=True)
    await authorize_task_payload(session, current_user, payload, require_client_id=True)
    task = await task_repo.create_task(
        session,
        task_type=request.task_type,
        payload=_serialize_task_payload(payload),
    )
    await session.commit()
    await session.refresh(task)
    return TaskCreateResponse(task_id=task.id, status=_task_status_value(task.status))


async def get_task_status_service(
    session: AsyncSession,
    *,
    current_user: Accountant,
    task_id: UUID,
) -> TaskStatusResponse | None:
    """Return task status after checking payload-scoped access."""
    task = await task_repo.get_task(session, task_id)
    if not task:
        return None
    await authorize_task_payload(session, current_user, task.payload or {})
    return TaskStatusResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=_task_status_value(task.status),
        result=task.result,
        error=_public_task_error(task.error),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )

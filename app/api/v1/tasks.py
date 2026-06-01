from fastapi import APIRouter, Depends, HTTPException, Path, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.common.schemas import Role
from app.db.database import get_session
from app.models.users import User
from app.schemas.tasks import TaskCreateRequest, TaskCreateResponse, TaskStatusResponse
from app.api.dependencies.auth import require_role
from app.services.tasks import enqueue_task_service, get_task_status_service
from app.common.rate_limit import limiter, TASK_SUBMIT_LIMIT, TASK_STATUS_LIMIT

router = APIRouter(tags=["tasks"])


@router.post(
    "/tasks",
    response_model=TaskCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a background task",
    description="Submits an asynchronous background task to the queue. Only 'summarize_client' is supported today.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user cannot access the requested client"},
        400: {"description": "Unsupported or invalid task_type"},
        422: {"description": "Invalid task payload"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(TASK_SUBMIT_LIMIT)
async def enqueue_task(
    request: Request,
    payload: TaskCreateRequest,
    current_user: User = Depends(
        require_role(Role.accountant, Role.firm_admin, Role.superuser)
    ),
    session: AsyncSession = Depends(get_session),
) -> TaskCreateResponse:
    """Submit a background task."""
    try:
        return await enqueue_task_service(
            session,
            current_user=current_user,
            request=payload,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except TypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    summary="Get background task status",
    description="Returns the current status and result of a previously submitted background task.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user cannot access the task client"},
        404: {"description": "Task not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(TASK_STATUS_LIMIT)
async def task_status(
    request: Request,
    task_id: UUID = Path(...),
    current_user: User = Depends(
        require_role(Role.accountant, Role.firm_admin, Role.superuser)
    ),
    session: AsyncSession = Depends(get_session),
) -> TaskStatusResponse:
    """Get background task status."""
    response = await get_task_status_service(
        session,
        current_user=current_user,
        task_id=task_id,
    )
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="task not found"
        )
    return response

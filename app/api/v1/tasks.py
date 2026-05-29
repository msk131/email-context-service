from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.repositories import tasks as task_repo

router = APIRouter(tags=["tasks"])


@router.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
async def enqueue_task(payload: dict, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    # Only 'summarize_client' supported for now
    task_type = payload.get("task_type")
    if task_type != "summarize_client":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unsupported task_type")
    task_payload = payload.get("payload") or {}
    task = await task_repo.create_task(session, task_type=task_type, payload=task_payload)
    return {"task_id": task.id, "status": task.status}


@router.get("/tasks/{task_id}")
async def task_status(task_id: int, session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    task = await task_repo.get_task(session, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return {
        "task_id": task.id,
        "task_type": task.task_type,
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }

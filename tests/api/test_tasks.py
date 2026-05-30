from types import SimpleNamespace
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1 import tasks as tasks_api
from app.common.exceptions import AccessDeniedError
from app.schemas.tasks import SummarizeClientPayload, TaskCreateRequest
from app.services import tasks as tasks_service


class FakeSession:
    def __init__(self, client):
        self.client = client

    async def get(self, model, item_id):
        return self.client

    async def commit(self):
        pass

    async def refresh(self, item):
        pass


def _user(firm_id=1, role="accountant"):
    return SimpleNamespace(firm_id=firm_id, role=SimpleNamespace(value=role))


@pytest.mark.asyncio
async def test_enqueue_task_requires_client_id():
    with pytest.raises(ValueError) as exc:
        await tasks_service.enqueue_task_service(
            FakeSession(client=None),
            current_user=_user(),
            request=SimpleNamespace(
                task_type="summarize_client",
                payload=SimpleNamespace(model_dump=lambda exclude_none=True: {}),
            ),
        )

    assert "client_id" in str(exc.value)


@pytest.mark.asyncio
async def test_enqueue_task_authorizes_client_access(monkeypatch):
    async def fake_create_task(session, task_type, payload):
        return SimpleNamespace(id=uuid4(), status="pending")

    monkeypatch.setattr(tasks_service.task_repo, "create_task", fake_create_task)

    response = await tasks_api.enqueue_task.__wrapped__(
        SimpleNamespace(),
        TaskCreateRequest(
            task_type="summarize_client",
            payload=SummarizeClientPayload(client_id=1, force=True),
        ),
        current_user=_user(firm_id=7),
        session=FakeSession(client=SimpleNamespace(firm_id=7)),
    )

    assert str(response.task_id)
    assert response.status == "pending"


@pytest.mark.asyncio
async def test_enqueue_task_rejects_cross_firm_client(monkeypatch):
    async def fake_create_task(session, task_type, payload):
        raise AssertionError("task should not be created")

    monkeypatch.setattr(tasks_service.task_repo, "create_task", fake_create_task)

    with pytest.raises(AccessDeniedError):
        await tasks_api.enqueue_task.__wrapped__(
            SimpleNamespace(),
            TaskCreateRequest(
                task_type="summarize_client",
                payload=SummarizeClientPayload(client_id=1),
            ),
            current_user=_user(firm_id=1),
            session=FakeSession(client=SimpleNamespace(firm_id=2)),
        )


def test_task_payload_rejects_invalid_date_range():
    with pytest.raises(ValidationError) as exc:
        SummarizeClientPayload(
            client_id=1,
            start_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    assert "start_date must be before end_date" in str(exc.value)


@pytest.mark.asyncio
async def test_task_status_sanitizes_failure_error(monkeypatch):
    task_id = uuid4()

    async def fake_get_task(session, requested_task_id):
        assert requested_task_id == task_id
        return SimpleNamespace(
            id=task_id,
            task_type="summarize_client",
            status="failed",
            payload={"client_id": 1},
            result=None,
            error="ValueError: bad input\nTraceback (most recent call last): ...",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(tasks_service.task_repo, "get_task", fake_get_task)

    response = await tasks_service.get_task_status_service(
        FakeSession(client=SimpleNamespace(firm_id=1)),
        current_user=_user(firm_id=1),
        task_id=task_id,
    )

    assert (
        response.error == "Task failed. Check server logs with the task_id for details."
    )
    assert "Traceback" not in response.error

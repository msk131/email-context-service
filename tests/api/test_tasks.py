from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.v1 import tasks as tasks_api
from app.common.exceptions import AccessDeniedError
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
    with pytest.raises(HTTPException) as exc:
        await tasks_api.enqueue_task.__wrapped__(
            SimpleNamespace(),
            {"task_type": "summarize_client", "payload": {}},
            current_user=_user(),
            session=FakeSession(client=None),
        )

    assert exc.value.status_code == 422
    assert "client_id" in exc.value.detail


@pytest.mark.asyncio
async def test_enqueue_task_authorizes_client_access(monkeypatch):
    async def fake_create_task(session, task_type, payload):
        return SimpleNamespace(id=uuid4(), status="pending")

    monkeypatch.setattr(tasks_service.task_repo, "create_task", fake_create_task)

    response = await tasks_api.enqueue_task.__wrapped__(
        SimpleNamespace(),
        {"task_type": "summarize_client", "payload": {"client_id": 1, "force": True}},
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
            {"task_type": "summarize_client", "payload": {"client_id": 1}},
            current_user=_user(firm_id=1),
            session=FakeSession(client=SimpleNamespace(firm_id=2)),
        )

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.v1 import summaries as summaries_api
from app.services import summary_tasks


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
async def test_refresh_summary_enqueues_task_for_external_worker(monkeypatch):
    task_id = uuid4()

    async def fake_create_task(session, task_type, payload):
        assert task_type == "summarize_client"
        assert payload == {
            "client_id": 42,
            "force": True,
            "start_date": "2026-01-01T00:00:00+00:00",
            "end_date": "2026-01-31T00:00:00+00:00",
        }
        return SimpleNamespace(id=task_id, status=SimpleNamespace(value="pending"))

    async def fake_load_client(session, client_id):
        assert client_id == 42
        return SimpleNamespace(firm_id=7)

    monkeypatch.setattr(summary_tasks, "load_client", fake_load_client)
    monkeypatch.setattr(summary_tasks.task_repo, "create_task", fake_create_task)

    response = await summaries_api.refresh_summary.__wrapped__(
        SimpleNamespace(state=SimpleNamespace(request_id="req-refresh")),
        client_id=42,
        force=True,
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        current_user=_user(firm_id=7),
        session=FakeSession(client=SimpleNamespace(firm_id=7)),
    )

    assert response.task_id == task_id
    assert response.status == "pending"

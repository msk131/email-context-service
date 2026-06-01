from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.common.models import RoleEnum
from app.models.user import User
from app.models.client import Client
from app.schemas.emails import GraphMessage
from app.services import emails as email_service


def _message() -> GraphMessage:
    return GraphMessage(
        **{
            "from": {
                "emailAddress": {
                    "address": "accountant@example.org",
                    "name": "John Accountant",
                }
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": "akshar@example.org",
                        "name": "Akshar Patel",
                    }
                }
            ],
            "sentDateTime": datetime(2026, 5, 29, 8, 12),
            "body": {"contentType": "HTML", "content": "Please send the missing form."},
        }
    )


@pytest.mark.asyncio
async def test_summary_task_payload_includes_email_timestamp(monkeypatch):
    captured_payload = {}
    task_id = uuid4()

    async def fake_create_task(session, task_type, payload):
        captured_payload.update(payload)
        return SimpleNamespace(id=task_id, status=SimpleNamespace(value="pending"))

    monkeypatch.setattr(email_service.task_repo, "create_task", fake_create_task)

    sent_at = datetime(2026, 5, 29, 8, 12)
    task = await email_service._enqueue_summary_refresh(object(), 1, sent_at)

    assert task.id == task_id
    assert captured_payload == {
        "client_id": 1,
        "force": False,
        "end_date": "2026-05-29T08:12:00",
    }


@pytest.mark.asyncio
async def test_mock_email_client_lookup_is_scoped_to_user_firm(monkeypatch):
    calls = {}

    async def fake_get_client_by_firm_and_email(session, *, firm_id, external_email):
        calls["firm_id"] = firm_id
        calls["external_email"] = external_email
        return Client(
            id=11, firm_id=firm_id, name="Akshar Patel", external_email=external_email
        )

    async def fail_global_lookup(session, external_email, *, limit=2):
        raise AssertionError(
            "non-superuser mock capture should not use global client lookup"
        )

    monkeypatch.setattr(
        email_service, "get_client_by_firm_and_email", fake_get_client_by_firm_and_email
    )
    monkeypatch.setattr(email_service, "list_clients_by_email", fail_global_lookup)

    user = User(
        id=5,
        firm_id=7,
        email="accountant@example.org",
        password_hash="hash",
        role=RoleEnum.accountant,
    )

    client = await email_service._get_client_by_email_for_user(
        object(),
        current_user=user,
        external_email="akshar@example.org",
    )

    assert client.id == 11
    assert calls == {"firm_id": 7, "external_email": "akshar@example.org"}


@pytest.mark.asyncio
async def test_superuser_mock_email_lookup_rejects_ambiguous_client_email(monkeypatch):
    async def fake_list_clients_by_email(session, external_email, *, limit=2):
        return [
            Client(id=11, firm_id=7, name="Akshar One", external_email=external_email),
            Client(id=12, firm_id=8, name="Akshar Two", external_email=external_email),
        ]

    monkeypatch.setattr(
        email_service, "list_clients_by_email", fake_list_clients_by_email
    )

    user = User(
        id=5,
        firm_id=7,
        email="super@example.org",
        password_hash="hash",
        role=RoleEnum.superuser,
    )

    with pytest.raises(Exception) as exc:
        await email_service._get_client_by_email_for_user(
            object(),
            current_user=user,
            external_email="akshar@example.org",
        )

    assert getattr(exc.value, "status_code", None) == 409

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks

from app.common.models import RoleEnum
from app.api.v1 import setup as setup_api
from app.models.auth import Accountant
from app.models.clients import Client
from app.schemas.emails import EmailCaptureResponse, GraphMessage, GraphSendMailRequest
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
async def test_mock_send_schedules_summary_task(monkeypatch):
    async def fake_mock_send_email(session, *, current_user, request):
        return EmailCaptureResponse(
            message=request.message,
            summary_task_id=42,
            summary_task_status="pending",
        )

    monkeypatch.setattr(setup_api, "mock_send_email", fake_mock_send_email)

    background_tasks = BackgroundTasks()
    response = await setup_api.create_mock_sent_email(
        SimpleNamespace(state=SimpleNamespace(request_id="req-send")),
        GraphSendMailRequest(message=_message()),
        background_tasks,
        current_user=object(),
        session=object(),
    )

    assert response.summary_task_id == 42
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is setup_api.process_task_by_id
    assert background_tasks.tasks[0].args == (42, "req-send")


@pytest.mark.asyncio
async def test_mock_receive_schedules_summary_task(monkeypatch):
    async def fake_mock_receive_email(session, *, current_user, request):
        return EmailCaptureResponse(
            message=request,
            summary_task_id=43,
            summary_task_status="pending",
        )

    monkeypatch.setattr(setup_api, "mock_receive_email", fake_mock_receive_email)

    background_tasks = BackgroundTasks()
    response = await setup_api.create_mock_received_email(
        SimpleNamespace(state=SimpleNamespace(request_id="req-receive")),
        _message(),
        background_tasks,
        current_user=object(),
        session=object(),
    )

    assert response.summary_task_id == 43
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is setup_api.process_task_by_id
    assert background_tasks.tasks[0].args == (43, "req-receive")


@pytest.mark.asyncio
async def test_summary_task_payload_includes_email_timestamp(monkeypatch):
    captured_payload = {}

    async def fake_create_task(session, task_type, payload):
        captured_payload.update(payload)
        return SimpleNamespace(id=44, status=SimpleNamespace(value="pending"))

    monkeypatch.setattr(email_service.task_repo, "create_task", fake_create_task)

    sent_at = datetime(2026, 5, 29, 8, 12)
    task = await email_service._enqueue_summary_refresh(object(), 1, sent_at)

    assert task.id == 44
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
        return Client(id=11, firm_id=firm_id, name="Akshar Patel", external_email=external_email)

    async def fail_global_lookup(session, external_email):
        raise AssertionError("non-superuser mock capture should not use global client lookup")

    monkeypatch.setattr(email_service, "get_client_by_firm_and_email", fake_get_client_by_firm_and_email)
    monkeypatch.setattr(email_service, "get_client_by_email", fail_global_lookup)

    user = Accountant(
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

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

import app.services.conversation as conversation_service
import app.services.summary_refresh as summary_refresh
import app.services.summaries as summaries
from app.common.schemas import Role
from app.schemas.summaries import (
    ConversationRequest,
    ConversationResponse,
    EmailSearchMatch,
)


class DummySummary:
    def __init__(self, refreshed_at: datetime):
        self.refreshed_at = refreshed_at


class DummyUser:
    role = Role.accountant
    firm_id = 1


@pytest.mark.asyncio
async def test_maybe_refresh_summary_creates_summary_when_missing(monkeypatch):
    async def fake_get_summary_record(session, client_id):
        return None

    called = []

    async def fake_refresh(session, client_id, start_date=None, end_date=None, force=False):
        called.append(("refresh", client_id))
        return "ok"

    monkeypatch.setattr(summary_refresh, "get_summary_record", fake_get_summary_record)
    monkeypatch.setattr(summary_refresh, "refresh_client_summary", fake_refresh)

    await summaries.maybe_refresh_summary_for_new_email(None, 123)

    assert called == [("refresh", 123)]


@pytest.mark.asyncio
async def test_maybe_refresh_summary_refreshes_after_five_new_emails(monkeypatch):
    async def fake_get_summary_record(session, client_id):
        return DummySummary(datetime(2026, 1, 1))

    async def fake_count_newly_captured_emails(session, client_id, after):
        return 5

    called = []

    async def fake_refresh(session, client_id, start_date=None, end_date=None, force=False):
        called.append(("refresh", client_id))
        return "ok"

    monkeypatch.setattr(summary_refresh, "get_summary_record", fake_get_summary_record)
    monkeypatch.setattr(
        summary_refresh,
        "count_newly_captured_emails",
        fake_count_newly_captured_emails,
    )
    monkeypatch.setattr(summary_refresh, "refresh_client_summary", fake_refresh)

    await summaries.maybe_refresh_summary_for_new_email(None, 123)

    assert called == [("refresh", 123)]


@pytest.mark.asyncio
async def test_maybe_refresh_summary_invalidates_cache_when_less_than_five_new_emails(monkeypatch):
    async def fake_get_summary_record(session, client_id):
        return DummySummary(datetime(2026, 1, 1))

    async def fake_count_newly_captured_emails(session, client_id, after):
        return 3

    called = []

    async def fake_invalidate(client_id):
        called.append(("invalidate", client_id))

    monkeypatch.setattr(summary_refresh, "get_summary_record", fake_get_summary_record)
    monkeypatch.setattr(
        summary_refresh,
        "count_newly_captured_emails",
        fake_count_newly_captured_emails,
    )
    monkeypatch.setattr(summary_refresh, "invalidate_summary_cache", fake_invalidate)

    await summaries.maybe_refresh_summary_for_new_email(None, 123)

    assert called == [("invalidate", 123)]


def test_conversation_request_rejects_structured_filters():
    with pytest.raises(ValidationError):
        ConversationRequest(
            question="What is blocking Akshar in the last 7 days?",
            client_id=123,
        )


def test_conversation_search_query_removes_question_fillers():
    query = conversation_service._conversation_search_query(
        "Can you summarize the latest emails about the missing form?"
    )

    assert query == "missing form"


@pytest.mark.asyncio
async def test_conversation_extracts_filters_from_question(monkeypatch):
    calls = []

    async def fake_infer_client_id(session, *, current_user, question):
        return 42

    async def fake_search_email_context(
        session,
        *,
        current_user,
        query,
        client_id=None,
        start_date=None,
        end_date=None,
        limit=25,
    ):
        calls.append(
            {
                "query": query,
                "client_id": client_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            }
        )
        return type("SearchResponse", (), {"results": []})()

    monkeypatch.setattr(
        conversation_service,
        "_infer_conversation_client_id",
        fake_infer_client_id,
    )
    monkeypatch.setattr(conversation_service, "search_email_context", fake_search_email_context)

    response = await summaries.answer_email_context_question(
        None,
        current_user=DummyUser(),
        question="For Akshar, summarize the latest 3 emails from the last 7 days.",
    )

    assert isinstance(response, ConversationResponse)
    assert calls[0]["query"] == "akshar"
    assert calls[0]["client_id"] == 42
    assert calls[0]["limit"] == 3
    assert calls[0]["end_date"] is not None
    assert calls[0]["start_date"] is not None
    assert calls[0]["end_date"] - calls[0]["start_date"] >= timedelta(days=6, hours=23)


@pytest.mark.asyncio
async def test_conversation_retries_without_inferred_filters(monkeypatch):
    calls = []

    async def fake_infer_client_id(session, *, current_user, question):
        return 42

    async def fake_search_email_context(
        session,
        *,
        current_user,
        query,
        client_id=None,
        start_date=None,
        end_date=None,
        limit=25,
    ):
        calls.append(
            {
                "query": query,
                "client_id": client_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            }
        )
        if len(calls) == 1:
            return type("SearchResponse", (), {"results": []})()
        source = EmailSearchMatch(
            id=1,
            client_id=42,
            client_name="Akshar",
            sender_email="akshar@example.com",
            recipients=["cpa@example.com"],
            subject="Missing form",
            snippet="Please send the missing form.",
            sent_at=datetime(2026, 5, 1, 12, 0),
            relevance_score=2,
        )
        return type("SearchResponse", (), {"results": [source]})()

    monkeypatch.setattr(
        conversation_service,
        "_infer_conversation_client_id",
        fake_infer_client_id,
    )
    monkeypatch.setattr(conversation_service, "search_email_context", fake_search_email_context)

    response = await summaries.answer_email_context_question(
        None,
        current_user=DummyUser(),
        question="For Akshar, what about the missing form today?",
    )

    assert response.source_email_count == 1
    assert calls[0]["client_id"] == 42
    assert calls[0]["start_date"] is not None
    assert calls[1]["client_id"] is None
    assert calls[1]["start_date"] is None
    assert calls[1]["query"] == "akshar missing form"

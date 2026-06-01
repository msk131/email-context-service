from datetime import datetime
from types import SimpleNamespace

import pytest

from app.common.schemas import Role
from app.models.client import Client
from app.models.email import Email
from app.services import email_search
from app.services.email_search import _snippet, _to_search_match


def test_snippet_focuses_on_first_query_match():
    text = (
        "Intro text. "
        + ("x" * 80)
        + " Missing 1099-INT from First Bank is blocking filing."
    )

    snippet = _snippet(text, "1099-INT")

    assert "1099-INT" in snippet
    assert len(snippet) <= 223


def test_search_match_contains_relevance_and_client_context():
    client = Client(
        id=10, firm_id=3, name="Akshar Patel", external_email="akshar@example.com"
    )
    email = Email(
        id=55,
        client_id=10,
        sender_email="akshar@example.com",
        recipients=["cpa@example.org"],
        subject="Missing 1099-INT",
        body="Please confirm whether the missing 1099-INT is still needed.",
        sent_at=datetime(2026, 5, 1, 12, 0, 0),
    )

    match = _to_search_match("missing 1099", email, client)

    assert match.client_name == "Akshar Patel"
    assert match.relevance_score >= 2
    assert "1099-INT" in match.subject


def test_search_match_exposes_only_to_recipients():
    client = Client(
        id=10, firm_id=3, name="Akshar Patel", external_email="akshar@example.com"
    )
    email = Email(
        id=55,
        client_id=10,
        sender={"emailAddress": {"address": "akshar@example.com"}},
        sender_address="akshar@example.com",
        to_recipients=[{"emailAddress": {"address": "cpa@example.org"}}],
        cc_recipients=[{"emailAddress": {"address": "reviewer@example.org"}}],
        bcc_recipients=[{"emailAddress": {"address": "hidden@example.org"}}],
        subject="Missing 1099-INT",
        body={"contentType": "Text", "content": "Please confirm the missing form."},
        sent_at=datetime(2026, 5, 1, 12, 0, 0),
    )

    match = _to_search_match("missing", email, client)

    assert match.sender_email == "akshar@example.com"
    assert match.recipients == ["cpa@example.org"]


@pytest.mark.asyncio
async def test_search_email_context_matches_email_without_summary(monkeypatch):
    client = Client(
        id=10, firm_id=3, name="Akshar Patel", external_email="akshar@example.com"
    )
    email = Email(
        id=55,
        client_id=10,
        sender_email="akshar@example.com",
        recipients=["cpa@example.org"],
        subject="Missing form",
        body={"contentType": "Text", "content": "Please send the missing form today."},
        sent_at=datetime(2026, 5, 1, 12, 0, 0),
    )

    async def fake_list_accessible_email_rows(*args, **kwargs):
        return [(email, client)]

    monkeypatch.setattr(
        email_search,
        "list_accessible_email_rows",
        fake_list_accessible_email_rows,
    )

    response = await email_search.search_email_context(
        None,
        current_user=SimpleNamespace(
            role=SimpleNamespace(value=Role.superuser.value), firm_id=1
        ),
        query=" the missing form",
        limit=25,
    )

    assert response.query == "the missing form"
    assert response.total == 1
    assert response.results[0].subject == "Missing form"

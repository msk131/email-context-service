from datetime import datetime

from app.models.clients import Client
from app.models.summaries import Email
from app.services.summaries import _snippet, _to_search_match


def test_snippet_focuses_on_first_query_match():
    text = "Intro text. " + ("x" * 80) + " Missing 1099-INT from First Bank is blocking filing."

    snippet = _snippet(text, "1099-INT")

    assert "1099-INT" in snippet
    assert len(snippet) <= 223


def test_search_match_contains_relevance_and_client_context():
    client = Client(id=10, firm_id=3, name="Akshar Patel", external_email="akshar@example.com")
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

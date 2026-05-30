"""Email context search services."""

import re
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role
from app.models.auth import Accountant
from app.models.clients import Client
from app.models.summaries import Email
from app.repositories.summaries import list_accessible_email_rows, load_client
from app.schemas.summaries import EmailSearchMatch, EmailSearchResponse
from app.services.clients import authorize_client_for_user

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SENSITIVE_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # US SSN
    re.compile(r"\b\d{2}-\d{7}\b"),  # EIN
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),  # payment card-like numbers
]


def _visible_recipient_addresses(email: Email) -> list[str]:
    """Return recipient addresses that are safe to expose in API responses."""
    recipients = []
    for recipient in email.to_recipients or []:
        email_address = recipient.get("emailAddress") or {}
        address = email_address.get("address")
        if address:
            recipients.append(address)
    return recipients


def _score_email(
    query: str, email: Email, client: Client, terms: list[str] | None = None
) -> int:
    terms = terms if terms is not None else _search_terms(query)
    haystack = " ".join(
        [
            email.subject,
            email.body_text,
            email.sender_email,
            client.name,
            client.external_email,
        ]
    ).lower()
    return sum(1 for term in terms if term in haystack)


def _search_terms(query: str) -> list[str]:
    """Normalize search terms once for DB filtering and in-memory ranking."""
    return [term for term in query.lower().split() if term]


def _snippet(text: str, query: str, max_length: int = 220) -> str:
    lowered = text.lower()
    first_index = 0
    for term in query.lower().split():
        index = lowered.find(term)
        if index >= 0:
            first_index = max(0, index - 60)
            while first_index > 0 and not text[first_index - 1].isspace():
                first_index -= 1
            break
    snippet = text[first_index : first_index + max_length].strip()
    suffix = "..." if first_index + max_length < len(text) else ""
    return _redact_sensitive_text(snippet + suffix)


def _redact_sensitive_text(text: str) -> str:
    """Remove control characters and mask common sensitive identifiers."""
    sanitized = _CONTROL_CHARS_RE.sub("", text)
    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def _to_search_match(
    query: str,
    email: Email,
    client: Client,
    relevance_score: int | None = None,
) -> EmailSearchMatch:
    if relevance_score is None:
        relevance_score = _score_email(query, email, client)
    return EmailSearchMatch(
        id=email.id,
        client_id=email.client_id,
        client_name=client.name,
        sender_email=email.sender_email,
        recipients=_visible_recipient_addresses(email),
        subject=email.subject,
        snippet=_snippet(email.body_text, query),
        sent_at=email.sent_at,
        relevance_score=relevance_score,
    )


async def search_email_context(
    session: AsyncSession,
    *,
    current_user: Accountant,
    query: str,
    client_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 25,
) -> EmailSearchResponse:
    """Search accessible email content using natural-language keywords."""
    normalized_query = query.strip()
    if len(normalized_query) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="query must contain at least 2 characters",
        )
    if len(normalized_query) > 256:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="query must contain at most 256 characters",
        )
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be before end_date",
        )
    if client_id is not None:
        client = await load_client(session, client_id)
        await authorize_client_for_user(
            current_user,
            client,
            Role(current_user.role.value),
        )

    candidate_limit = min(max(limit * 10, 100), 1000)
    search_terms = _search_terms(normalized_query)
    rows = await list_accessible_email_rows(
        session,
        role=Role(current_user.role.value),
        firm_id=current_user.firm_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        search_terms=search_terms,
        limit=candidate_limit,
    )
    matches = []
    for email, client in rows:
        score = _score_email(normalized_query, email, client, search_terms)
        if score > 0:
            matches.append(_to_search_match(normalized_query, email, client, score))
    matches = sorted(
        matches,
        key=lambda item: (item.relevance_score, item.sent_at),
        reverse=True,
    )[:limit]
    return EmailSearchResponse(
        query=normalized_query,
        total=len(matches),
        results=matches,
    )

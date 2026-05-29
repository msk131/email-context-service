"""Email context search services."""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role
from app.llm.embeddings import embed_text
from app.models.auth import Accountant
from app.models.clients import Client
from app.models.summaries import Email
from app.repositories.summaries import list_accessible_email_summary_rows, load_client
from app.schemas.summaries import EmailSearchMatch, EmailSearchResponse
from app.services.clients import authorize_client_for_user
from app.services.search import rank_email_summary_rows


def _score_email(query: str, email: Email, client: Client) -> int:
    haystack = " ".join(
        [
            email.subject,
            email.body_text,
            email.sender_email,
            client.name,
            client.external_email,
        ]
    ).lower()
    return max(1, sum(1 for term in query.lower().split() if term in haystack))


def _snippet(text: str, query: str, max_length: int = 220) -> str:
    lowered = text.lower()
    first_index = 0
    for term in query.lower().split():
        index = lowered.find(term)
        if index >= 0:
            first_index = max(0, index - 60)
            break
    snippet = text[first_index:first_index + max_length].strip()
    return snippet + ("..." if first_index + max_length < len(text) else "")


def _to_search_match(query: str, email: Email, client: Client) -> EmailSearchMatch:
    return EmailSearchMatch(
        id=email.id,
        client_id=email.client_id,
        client_name=client.name,
        sender_email=email.sender_email,
        recipients=email.recipients,
        subject=email.subject,
        snippet=_snippet(email.body_text, query),
        sent_at=email.sent_at,
        relevance_score=_score_email(query, email, client),
    )


async def search_email_context(
    session: AsyncSession,
    *,
    current_user: Accountant,
    query: str,
    client_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 25,
) -> EmailSearchResponse:
    """Search accessible email content using natural-language keywords."""
    if len(query.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="query must contain at least 2 characters",
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

    rows = await list_accessible_email_summary_rows(
        session,
        role=Role(current_user.role.value),
        firm_id=current_user.firm_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
    )
    ranked_rows = rank_email_summary_rows(
        rows,
        query_embedding=embed_text(query),
        limit=limit,
    )
    matches = sorted(
        [_to_search_match(query, email, client) for email, client in ranked_rows],
        key=lambda item: (item.relevance_score, item.sent_at),
        reverse=True,
    )
    return EmailSearchResponse(query=query, total=len(matches), results=matches)

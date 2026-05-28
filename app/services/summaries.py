"""Summaries service - business logic for email summarization."""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_summary_cache, invalidate_summary_cache, set_summary_cache
from app.llm import GeminiService
from app.models.clients import Client
from app.models.auth import Accountant
from app.models.summaries import Email, EmailSummary, SummarizationLog
from app.schemas.summaries import (
    ConversationResponse,
    EmailSearchMatch,
    EmailSearchResponse,
    SummaryResponse,
    SummaryResult,
)
from app.repositories.summaries import (
    load_client,
    get_summary_record,
    get_emails,
    count_new_emails,
    search_accessible_emails,
)
from app.utils import decrypt_text, encrypt_text, normalize_date_range
from app.common.schemas import Role


async def refresh_client_summary(
    session: AsyncSession,
    client_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    force: bool = False,
) -> SummaryResponse:
    """Refresh/generate client email summary using LLM."""
    try:
        start_date, end_date = normalize_date_range(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    
    # Load client and emails
    client = await load_client(session, client_id)
    emails = await get_emails(session, client_id, start_date, end_date)
    if not emails:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No emails found for the requested range"
        )
    
    # Check if refresh needed
    summary_record = await get_summary_record(session, client_id)
    if summary_record and not force:
        new_email_count = await count_new_emails(session, client_id, summary_record.refreshed_at)
        if new_email_count < 5:
            return SummaryResponse(
                client_id=client.id,
                client_name=client.name,
                firm_id=client.firm_id,
                refreshed_at=summary_record.refreshed_at,
                skipped=True,
                reason="Fewer than 5 new emails have arrived since last refresh",
            )
    
    # Generate summary via LLM
    gemini = GeminiService()
    payload = gemini.summarize(
        [
            {
                "sender_email": email.sender_email,
                "recipients": email.recipients,
                "subject": email.subject,
                "body": email.body,
                "sent_at": email.sent_at,
            }
            for email in emails
        ],
        start_date,
        end_date,
    )
    result = await payload
    
    # Save summary to database
    encrypted = encrypt_text(result["summary_text"])
    if not summary_record:
        summary_record = EmailSummary(client_id=client.id)
        session.add(summary_record)
    
    summary_record.summary_encrypted = encrypted
    summary_record.actors = result.get("actors", [])
    summary_record.concluded_discussions = result.get("concluded_discussions", [])
    summary_record.open_action_items = result.get("open_action_items", [])
    summary_record.email_count_analyzed = len(emails)
    summary_record.token_in = int(result.get("token_in", 0))
    summary_record.token_out = int(result.get("token_out", 0))
    summary_record.refreshed_at = datetime.utcnow()
    
    # Log the operation
    session.add(
        SummarizationLog(
            client_id=client.id,
            email_count=len(emails),
            token_in=summary_record.token_in,
            token_out=summary_record.token_out,
            started_at=start_date,
            completed_at=datetime.utcnow(),
        )
    )
    
    await session.commit()
    await session.refresh(summary_record)
    await invalidate_summary_cache(client_id)
    
    # Return response
    response = SummaryResult(
        summary=decrypt_text(summary_record.summary_encrypted),
        actors=summary_record.actors,
        concluded_discussions=summary_record.concluded_discussions,
        open_action_items=summary_record.open_action_items,
        email_count_analyzed=summary_record.email_count_analyzed,
        refreshed_at=summary_record.refreshed_at,
        token_in=summary_record.token_in,
        token_out=summary_record.token_out,
    )
    summary_response = SummaryResponse(
        client_id=client.id,
        client_name=client.name,
        firm_id=client.firm_id,
        refreshed_at=summary_record.refreshed_at,
        skipped=False,
        result=response,
    )
    await set_summary_cache(client_id, summary_response.model_dump())
    return summary_response


async def read_cached_summary(session: AsyncSession, client_id: int) -> SummaryResponse:
    """Read cached summary for client."""
    # Try cache first
    cached = await get_summary_cache(client_id)
    if cached:
        return SummaryResponse(**cached)
    
    # Fall back to database
    summary_record = await get_summary_record(session, client_id)
    if summary_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No summary exists for this client"
        )
    
    client = await load_client(session, client_id)
    result = SummaryResult(
        summary=decrypt_text(summary_record.summary_encrypted),
        actors=summary_record.actors,
        concluded_discussions=summary_record.concluded_discussions,
        open_action_items=summary_record.open_action_items,
        email_count_analyzed=summary_record.email_count_analyzed,
        refreshed_at=summary_record.refreshed_at,
        token_in=summary_record.token_in,
        token_out=summary_record.token_out,
    )
    response = SummaryResponse(
        client_id=client.id,
        client_name=client.name,
        firm_id=client.firm_id,
        refreshed_at=summary_record.refreshed_at,
        skipped=False,
        result=result,
    )
    await set_summary_cache(client_id, response.model_dump())
    return response


def _score_email(query: str, email: Email, client: Client) -> int:
    haystack = " ".join(
        [
            email.subject,
            email.body,
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
        snippet=_snippet(email.body, query),
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

    rows = await search_accessible_emails(
        session,
        query=query,
        role=Role(current_user.role.value),
        firm_id=current_user.firm_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    matches = sorted(
        [_to_search_match(query, email, client) for email, client in rows],
        key=lambda item: (item.relevance_score, item.sent_at),
        reverse=True,
    )
    return EmailSearchResponse(query=query, total=len(matches), results=matches)


async def answer_email_context_question(
    session: AsyncSession,
    *,
    current_user: Accountant,
    question: str,
    client_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10,
) -> ConversationResponse:
    """Answer a natural-language question from accessible email context."""
    search_response = await search_email_context(
        session,
        current_user=current_user,
        query=question,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    if not search_response.results:
        return ConversationResponse(
            question=question,
            answer="No matching emails were found in the accessible context.",
            source_email_count=0,
            sources=[],
        )

    open_items = []
    concluded = []
    for source in search_response.results[:5]:
        text = f"{source.subject}: {source.snippet}"
        if any(word in text.lower() for word in ["need", "missing", "send", "action", "todo", "please"]):
            open_items.append(text)
        else:
            concluded.append(text)

    answer_parts = [
        f"Found {len(search_response.results)} relevant email(s).",
        f"Most relevant: {search_response.results[0].subject}.",
    ]
    if open_items:
        answer_parts.append("Likely open items: " + " | ".join(open_items[:3]))
    if concluded:
        answer_parts.append("Related context: " + " | ".join(concluded[:2]))

    return ConversationResponse(
        question=question,
        answer=" ".join(answer_parts),
        source_email_count=len(search_response.results),
        sources=search_response.results,
    )

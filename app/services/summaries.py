"""Summary use cases: read, refresh, enqueue, and reporting."""

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_summary_cache, invalidate_summary_cache, set_summary_cache
from app.common.schemas import Role
from app.common.time import utc_now
from app.core.logging_config import get_logger
from app.llm import LLMService
from app.llm.embeddings import embed_text_async
from app.models.client import Client
from app.models.email_summary import EmailSummary
from app.models.summarization_log import SummarizationLog
from app.models.user import User
from app.repositories import tasks as task_repo
from app.repositories.clients import count_clients_by_firm, get_client_by_id
from app.repositories.email_summaries import (
    count_summaries_by_firm,
    get_summary_record,
    list_summary_counts_by_firm,
)
from app.repositories.emails import (
    count_emails_captured_after,
    list_emails_for_summary,
)
from app.schemas.summaries import (
    ReportFirmClientCount,
    ReportFirmSummaryRow,
    ReportGlobalResponse,
    SummaryRefreshTaskResponse,
    SummaryResponse,
    SummaryResult,
)
from app.services.clients import authorize_client_for_user
from app.services.conversation import answer_email_context_question
from app.services.email_search import search_email_context
from app.utils import decrypt_text, encrypt_text, normalize_date_range

logger = get_logger("services.summaries")

# Backward-compatible service aliases used by older tests and call sites.
load_client = get_client_by_id
count_newly_captured_emails = count_emails_captured_after


def summary_response_from_record(
    client: Client,
    summary_record: EmailSummary,
    *,
    skipped: bool = False,
    reason: str | None = None,
) -> SummaryResponse:
    """Build an API summary response from ORM records."""
    result = None
    if not skipped:
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

    return SummaryResponse(
        client_id=client.id,
        client_name=client.name,
        firm_id=client.firm_id,
        refreshed_at=summary_record.refreshed_at,
        skipped=skipped,
        reason=reason,
        result=result,
    )


async def read_cached_summary(session: AsyncSession, client_id: int) -> SummaryResponse:
    """Read cached summary for client."""
    cached = await get_summary_cache(client_id)
    if cached:
        logger.info("Summary cache hit client_id=%s", client_id)
        return SummaryResponse(**cached)

    logger.info("Summary cache miss client_id=%s", client_id)
    summary_record = await get_summary_record(session, client_id)
    if summary_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No summary exists for this client",
        )

    client = await load_client(session, client_id)
    response = summary_response_from_record(client, summary_record)
    await set_summary_cache(client_id, response.model_dump())
    return response


async def read_authorized_summary(
    session: AsyncSession,
    *,
    current_user: User,
    client_id: int,
) -> SummaryResponse:
    """Read a cached summary after enforcing client access."""
    client = await load_client(session, client_id)
    await authorize_client_for_user(current_user, client, Role(current_user.role.value))
    return await read_cached_summary(session, client_id)


async def refresh_client_summary(
    session: AsyncSession,
    client_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    force: bool = False,
) -> SummaryResponse:
    """Refresh/generate client email summary using LLM."""
    logger.info(
        "Summary refresh requested client_id=%s force=%s start_date=%s end_date=%s",
        client_id,
        force,
        start_date,
        end_date,
    )
    try:
        start_date, end_date = normalize_date_range(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    client = await load_client(session, client_id)
    emails = await list_emails_for_summary(session, client_id, start_date, end_date)
    logger.info(
        "Loaded emails for summary client_id=%s email_count=%s", client_id, len(emails)
    )
    if not emails:
        logger.warning(
            "Summary refresh skipped; no emails found client_id=%s", client_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No emails found for the requested range",
        )

    summary_record = await get_summary_record(session, client_id)
    if summary_record and not force:
        new_email_count = await count_newly_captured_emails(
            session,
            client_id,
            summary_record.refreshed_at,
        )
        if new_email_count < 5:
            logger.info(
                "Summary refresh skipped client_id=%s new_email_count=%s refreshed_at=%s",
                client_id,
                new_email_count,
                summary_record.refreshed_at,
            )
            return summary_response_from_record(
                client,
                summary_record,
                skipped=True,
                reason="Fewer than 5 new emails have arrived since last refresh",
            )

    logger.info(
        "Calling LLM summarizer client_id=%s email_count=%s", client_id, len(emails)
    )
    started_at = utc_now()
    result = await LLMService().summarize(
        [
            {
                "sender_email": email.sender_email,
                "recipients": email.recipients,
                "subject": email.subject,
                "body": email.body_text,
                "sent_at": email.sent_at,
            }
            for email in emails
        ],
        start_date,
        end_date,
    )
    logger.info(
        "LLM summary generated client_id=%s token_in=%s token_out=%s",
        client_id,
        result.get("token_in", 0),
        result.get("token_out", 0),
    )

    if not summary_record:
        summary_record = EmailSummary(client_id=client.id)
        session.add(summary_record)

    summary_record.summary_encrypted = encrypt_text(result["summary_text"])
    summary_record.actors = result.get("actors", [])
    summary_record.concluded_discussions = result.get("concluded_discussions", [])
    summary_record.open_action_items = result.get("open_action_items", [])
    summary_record.email_count_analyzed = len(emails)
    summary_record.token_in = int(result.get("token_in", 0))
    summary_record.token_out = int(result.get("token_out", 0))
    summary_record.embedding = await embed_text_async(result["summary_text"])
    summary_record.refreshed_at = utc_now()

    session.add(
        SummarizationLog(
            client_id=client.id,
            email_count=len(emails),
            token_in=summary_record.token_in,
            token_out=summary_record.token_out,
            started_at=started_at,
            completed_at=utc_now(),
        )
    )

    await session.commit()
    await session.refresh(summary_record)
    await invalidate_summary_cache(client_id)
    logger.info(
        "Summary saved client_id=%s summary_id=%s", client_id, summary_record.id
    )

    response = summary_response_from_record(client, summary_record)
    await set_summary_cache(client_id, response.model_dump())
    return response


async def maybe_refresh_summary_for_new_email(
    session: AsyncSession, client_id: int
) -> None:
    """Ensure a client's summary record exists and refresh only when needed."""
    summary_record = await get_summary_record(session, client_id)
    if summary_record is None:
        logger.info("No existing summary; refreshing client_id=%s", client_id)
        await refresh_client_summary(session, client_id)
        return

    new_email_count = await count_newly_captured_emails(
        session,
        client_id,
        summary_record.refreshed_at,
    )
    if new_email_count >= 5:
        logger.info(
            "Refreshing summary after new emails client_id=%s new_email_count=%s",
            client_id,
            new_email_count,
        )
        await refresh_client_summary(session, client_id)
        return

    logger.info(
        "Invalidating summary cache after new email client_id=%s new_email_count=%s",
        client_id,
        new_email_count,
    )
    await invalidate_summary_cache(client_id)


async def enqueue_summary_refresh_task(
    session: AsyncSession,
    *,
    current_user: User,
    client_id: int,
    force: bool = False,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> SummaryRefreshTaskResponse:
    """Authorize and enqueue a summary refresh task."""
    client = await load_client(session, client_id)
    await authorize_client_for_user(current_user, client, Role(current_user.role.value))
    try:
        normalize_date_range(start_date, end_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    task = await task_repo.create_task(
        session,
        task_type="summarize_client",
        payload={
            "client_id": client_id,
            "force": force,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    )
    await session.commit()
    await session.refresh(task)
    return SummaryRefreshTaskResponse(task_id=task.id, status=task.status.value)


async def get_firm_summary_report(
    session: AsyncSession,
    *,
    current_user: User,
) -> ReportFirmClientCount:
    """Return summary coverage for the current user's firm."""
    count_with_summaries = await count_summaries_by_firm(session, current_user.firm_id)
    total_clients = await count_clients_by_firm(session, current_user.firm_id)
    coverage_percentage = (
        count_with_summaries / total_clients * 100 if total_clients > 0 else 0.0
    )
    return ReportFirmClientCount(
        client_count_with_summaries=count_with_summaries,
        total_clients_in_firm=total_clients,
        coverage_percentage=round(coverage_percentage, 1),
        generated_at=utc_now(),
    )


async def get_global_summary_report(session: AsyncSession) -> ReportGlobalResponse:
    """Return summary coverage grouped by firm."""
    rows = [
        ReportFirmSummaryRow(
            firm_id=firm_id,
            firm_name=firm_name,
            client_count_with_summaries=client_count,
        )
        for firm_id, firm_name, client_count in await list_summary_counts_by_firm(
            session
        )
    ]
    return ReportGlobalResponse(
        summaries_by_firm=rows,
        total_firms=len(rows),
        total_clients_with_summaries=sum(
            row.client_count_with_summaries for row in rows
        ),
        generated_at=utc_now(),
    )


__all__ = [
    "answer_email_context_question",
    "enqueue_summary_refresh_task",
    "get_firm_summary_report",
    "get_global_summary_report",
    "maybe_refresh_summary_for_new_email",
    "read_authorized_summary",
    "read_cached_summary",
    "refresh_client_summary",
    "search_email_context",
    "summary_response_from_record",
]

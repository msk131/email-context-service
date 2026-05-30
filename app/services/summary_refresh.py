"""Summary generation and refresh services."""
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import invalidate_summary_cache, set_summary_cache
from app.common.time import utc_now
from app.core.logging_config import get_logger
from app.llm import LLMService
from app.llm.embeddings import embed_text_async
from app.models.summaries import EmailSummary, SummarizationLog
from app.repositories.summaries import (
    count_newly_captured_emails,
    get_emails,
    get_summary_record,
    load_client,
)
from app.schemas.summaries import SummaryResponse
from app.services.summary_mapping import summary_response_from_record
from app.utils import encrypt_text, normalize_date_range

logger = get_logger("services.summary_refresh")


async def refresh_client_summary(
    session: AsyncSession,
    client_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
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
    emails = await get_emails(session, client_id, start_date, end_date)
    logger.info("Loaded emails for summary client_id=%s email_count=%s", client_id, len(emails))
    if not emails:
        logger.warning("Summary refresh skipped; no emails found client_id=%s", client_id)
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

    logger.info("Calling LLM summarizer client_id=%s email_count=%s", client_id, len(emails))
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
            started_at=start_date,
            completed_at=utc_now(),
        )
    )

    await session.commit()
    await session.refresh(summary_record)
    await invalidate_summary_cache(client_id)
    logger.info("Summary saved client_id=%s summary_id=%s", client_id, summary_record.id)

    response = summary_response_from_record(client, summary_record)
    await set_summary_cache(client_id, response.model_dump())
    return response


async def maybe_refresh_summary_for_new_email(session: AsyncSession, client_id: int) -> None:
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

"""Summaries API routes (HTTP layer).

Handles email summary operations.
Calls: services.summaries for business logic
Uses: models.summaries (ORM), schemas.summaries (validation)
"""
from datetime import datetime

from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.auth import Accountant
from app.api.dependencies.auth import require_role
from app.services.summaries import (
    answer_email_context_question,
    enqueue_summary_refresh_task,
    get_firm_summary_report,
    get_global_summary_report,
    read_authorized_summary,
    search_email_context,
)
from app.schemas.summaries import (
    ConversationRequest,
    ConversationResponse,
    EmailSearchResponse,
    ReportFirmClientCount,
    ReportGlobalResponse,
    SummaryRefreshTaskResponse,
    SummaryResponse,
)
from app.common.schemas import Role
from app.common.rate_limit import (
    limiter,
    SEARCH_LIMIT,
    CONVERSATION_LIMIT,
    REFRESH_LIMIT,
    SUMMARY_READ_LIMIT,
)

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get(
    "/search",
    response_model=EmailSearchResponse,
    summary="Search accessible email context",
    description=(
        "Search email subject, body, sender, client name, and client email across the "
        "current user's authorized scope. Accountants and firm admins are limited to their firm; "
        "superusers can search across all firms."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        422: {"description": "Invalid query, date range, or limit"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(SEARCH_LIMIT)
async def search_emails(
    request: Request,
    query: str = Query(..., min_length=2, max_length=256, description="Natural-language query or keywords."),
    client_id: int | None = Query(None, ge=1, description="Limit search to one client."),
    start_date: datetime | None = Query(None, description="Only include emails sent at or after this timestamp."),
    end_date: datetime | None = Query(None, description="Only include emails sent at or before this timestamp."),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of emails to return."),
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> EmailSearchResponse:
    """Natural-language keyword search over emails."""
    return await search_email_context(
        session,
        current_user=current_user,
        query=query,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )


@router.post(
    "/conversation",
    response_model=ConversationResponse,
    summary="Ask a question about accessible email context",
    description=(
        "Answers a natural-language question using matched emails as source context. "
        "The response includes source email snippets to ground the answer."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        422: {"description": "Invalid request body or date range"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(CONVERSATION_LIMIT)
async def conversation(
    request: Request,
    request_body: ConversationRequest = Body(...),
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> ConversationResponse:
    """Question-answer interface over email context."""
    return await answer_email_context_question(
        session,
        current_user=current_user,
        question=request_body.question,
    )


@router.get(
    "/reports/firm-summaries",
    response_model=ReportFirmClientCount,
    summary="Firm summary coverage report",
    description="Returns the count of clients in the current firm with generated summaries.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Firm admin role required"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("60/minute")
async def firm_summary_report(
    request: Request,
    current_user: Accountant = Depends(require_role(Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> ReportFirmClientCount:
    """Get count of clients with summaries for current firm."""
    return await get_firm_summary_report(
        session,
        current_user=current_user,
    )


@router.get(
    "/reports/global-summaries",
    response_model=ReportGlobalResponse,
    summary="Global summary coverage report",
    description="Returns summary coverage grouped by firm for superusers.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Superuser role required"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
async def global_summary_report(
    request: Request,
    current_user: Accountant = Depends(require_role(Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> ReportGlobalResponse:
    """Get summary report for all firms (superuser only)."""
    return await get_global_summary_report(session)


@router.get(
    "/{client_id}",
    response_model=SummaryResponse,
    summary="Fetch a client's cached summary",
    description="Returns the most recent generated client summary from cache or database, subject to authorization.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client or summary was not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(SUMMARY_READ_LIMIT)
async def read_summary(
    request: Request,
    client_id: int = Path(..., ge=1),
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    """Get cached summary for client."""
    return await read_authorized_summary(
        session,
        current_user=current_user,
        client_id=client_id,
    )


@router.post(
    "/{client_id}/refresh",
    response_model=SummaryRefreshTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Refresh a client's email summary",
    description=(
        "Enqueues a background refresh for a client's email summary. The LLM-backed "
        "summary work runs asynchronously; poll /tasks/{task_id} for completion."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client was not found"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(REFRESH_LIMIT)
async def refresh_summary(
    request: Request,
    client_id: int = Path(..., ge=1),
    force: bool = Query(False, description="Force refresh even if fewer than 5 new emails."),
    start_date: datetime | None = Query(
        None,
        description="Only include emails sent at or after this timestamp.",
    ),
    end_date: datetime | None = Query(
        None,
        description="Only include emails sent at or before this timestamp.",
    ),
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> SummaryRefreshTaskResponse:
    """Enqueue summary refresh for an external worker to process."""
    return await enqueue_summary_refresh_task(
        session,
        current_user=current_user,
        client_id=client_id,
        force=force,
        start_date=start_date,
        end_date=end_date,
    )

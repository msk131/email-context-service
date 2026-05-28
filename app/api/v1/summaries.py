"""Summaries API routes (HTTP layer).

Handles email summary operations.
Calls: services.summaries for business logic
Uses: models.summaries (ORM), schemas.summaries (validation)
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.auth import Accountant
from app.models.clients import Client
from app.models.firms import Firm
from app.models.summaries import EmailSummary
from app.services.auth import require_role
from app.services.clients import authorize_client_for_user
from app.services.summaries import (
    answer_email_context_question,
    refresh_client_summary,
    read_cached_summary,
    search_email_context,
)
from app.schemas.summaries import (
    ConversationRequest,
    ConversationResponse,
    EmailSearchResponse,
    ReportFirmClientCount,
    ReportFirmSummaryRow,
    ReportGlobalResponse,
    SummaryResponse,
)
from app.common.schemas import Role
from app.common.exceptions import EntityNotFoundError

router = APIRouter(prefix="/summaries", tags=["summaries"])


@router.get(
    "/search",
    response_model=EmailSearchResponse,
    summary="Search accessible email context",
    description=(
        "Search email subject, body, sender, client name, and client email across the "
        "current user's authorized scope. Accountants and firm admins are limited to "
        "their firm; superusers can search all firms."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        422: {"description": "Invalid query, date range, or limit"},
    },
)
async def search_emails(
    query: str = Query(..., min_length=2, description="Natural-language query or keywords."),
    client_id: Optional[int] = Query(None, description="Limit search to one client."),
    start_date: Optional[datetime] = Query(None, description="Only include emails sent at or after this timestamp."),
    end_date: Optional[datetime] = Query(None, description="Only include emails sent at or before this timestamp."),
    limit: int = Query(25, ge=1, le=100, description="Maximum number of emails to return."),
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> EmailSearchResponse:
    """Natural-language keyword search over emails."""
    if client_id is not None:
        client = await session.get(Client, client_id)
        if not client:
            raise EntityNotFoundError("Client", client_id)
        await authorize_client_for_user(current_user, client, current_user.role)
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
        "The response includes the source email snippets used to ground the answer."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        422: {"description": "Invalid request body or date range"},
    },
)
async def conversation(
    request: ConversationRequest = Body(...),
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> ConversationResponse:
    """Question-answer interface over email context."""
    if request.client_id is not None:
        client = await session.get(Client, request.client_id)
        if not client:
            raise EntityNotFoundError("Client", request.client_id)
        await authorize_client_for_user(current_user, client, current_user.role)
    return await answer_email_context_question(
        session,
        current_user=current_user,
        question=request.question,
        client_id=request.client_id,
        start_date=request.start_date,
        end_date=request.end_date,
        limit=request.limit,
    )


@router.get(
    "/{client_id}",
    response_model=SummaryResponse,
    summary="Read a client's cached summary",
    description="Returns the most recent generated summary for a client from cache or database.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client or summary was not found"},
    },
)
async def read_summary(
    client_id: int,
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    """Get cached summary for client."""
    client = await session.get(Client, client_id)
    if not client:
        raise EntityNotFoundError("Client", client_id)
    await authorize_client_for_user(current_user, client, current_user.role)
    return await read_cached_summary(session, client_id)


@router.post(
    "/{client_id}/refresh",
    response_model=SummaryResponse,
    summary="Refresh a client's email summary",
    description=(
        "Re-analyzes emails for the client and invalidates the summary cache. By default, "
        "the partial-refresh guard skips work when fewer than 5 new emails arrived since "
        "the last successful refresh. Set force=true to re-analyze anyway."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client or emails were not found"},
        422: {"description": "Invalid date range"},
    },
)
async def refresh_summary(
    client_id: int,
    start_date: Optional[datetime] = Query(None, description="Start of email analysis range. Defaults to earliest email."),
    end_date: Optional[datetime] = Query(None, description="End of email analysis range. Defaults to now."),
    force: bool = Query(False, description="Bypass the partial-refresh skip rule and re-analyze emails."),
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> SummaryResponse:
    """Refresh summary for client."""
    client = await session.get(Client, client_id)
    if not client:
        raise EntityNotFoundError("Client", client_id)
    await authorize_client_for_user(current_user, client, current_user.role)
    return await refresh_client_summary(session, client_id, start_date, end_date, force=force)


@router.get(
    "/reports/firm-summaries",
    response_model=ReportFirmClientCount,
    summary="Report firm summary coverage",
    description="Firm admins can view how many clients in their firm have generated summaries.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Firm admin role required"},
    },
)
async def firm_summary_report(
    current_user: Accountant = Depends(require_role(Role.firm_admin)),
    session: AsyncSession = Depends(get_session),
) -> ReportFirmClientCount:
    """Get count of clients with summaries for current firm."""
    result = await session.execute(
        select(func.count(EmailSummary.id))
        .join(Client, EmailSummary.client_id == Client.id)
        .where(Client.firm_id == current_user.firm_id)
    )
    count = int(result.scalar_one())
    return ReportFirmClientCount(client_count_with_summaries=count)


@router.get(
    "/reports/global-summaries",
    response_model=ReportGlobalResponse,
    summary="Report global summary coverage",
    description="Superusers can view summary coverage grouped by firm.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Superuser role required"},
    },
)
async def global_summary_report(
    current_user: Accountant = Depends(require_role(Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> ReportGlobalResponse:
    """Get summary report for all firms (superuser only)."""
    result = await session.execute(
        select(Firm.id, Firm.name, func.count(EmailSummary.id))
        .join(Client, Client.firm_id == Firm.id)
        .join(EmailSummary, EmailSummary.client_id == Client.id)
        .group_by(Firm.id, Firm.name)
    )
    rows = [
        ReportFirmSummaryRow(
            firm_id=firm_id,
            firm_name=firm_name,
            client_count_with_summaries=client_count
        )
        for firm_id, firm_name, client_count in result
    ]
    return ReportGlobalResponse(summaries_by_firm=rows)

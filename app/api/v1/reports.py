"""Reporting API routes."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_role
from app.common.rate_limit import limiter
from app.common.schemas import Role
from app.db.database import get_session
from app.models.user import User
from app.schemas.reports import ReportFirmClientCount, ReportGlobalResponse
from app.services.reports import (
    get_firm_client_report_coverage,
    get_global_client_report_coverage,
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get(
    "/firm-client-reports",
    response_model=ReportFirmClientCount,
    summary="Firm client-report coverage",
    description="Returns the count of clients in the current firm with generated client reports.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Firm admin role required"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("60/minute")
async def firm_client_report_coverage(
    request: Request,
    current_user: User = Depends(require_role(Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> ReportFirmClientCount:
    """Get count of clients with generated reports for current firm."""
    return await get_firm_client_report_coverage(
        session,
        current_user=current_user,
    )


@router.get(
    "/global-client-reports",
    response_model=ReportGlobalResponse,
    summary="Global client-report coverage",
    description="Returns client-report coverage grouped by firm for superusers.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Superuser role required"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
async def global_client_report_coverage(
    request: Request,
    current_user: User = Depends(require_role(Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> ReportGlobalResponse:
    """Get client-report coverage for all firms."""
    return await get_global_client_report_coverage(session)

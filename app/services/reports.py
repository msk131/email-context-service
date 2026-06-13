"""Reporting service layer."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time import utc_now
from app.models.user import User
from app.repositories.reports import (
    get_firm_client_report_counts,
    list_global_client_report_counts,
)
from app.schemas.reports import (
    ReportFirmClientCount,
    ReportFirmSummaryRow,
    ReportGlobalResponse,
)


async def get_firm_client_report_coverage(
    session: AsyncSession,
    *,
    current_user: User,
) -> ReportFirmClientCount:
    """Return client-report coverage for the current user's firm."""
    count_with_reports, total_clients = await get_firm_client_report_counts(
        session,
        current_user.firm_id,
    )
    coverage_percentage = (
        count_with_reports / total_clients * 100 if total_clients > 0 else 0.0
    )
    return ReportFirmClientCount(
        client_count_with_summaries=count_with_reports,
        total_clients_in_firm=total_clients,
        coverage_percentage=round(coverage_percentage, 1),
        generated_at=utc_now(),
    )


async def get_global_client_report_coverage(
    session: AsyncSession,
) -> ReportGlobalResponse:
    """Return client-report coverage grouped by firm."""
    rows = [
        ReportFirmSummaryRow(
            firm_id=firm_id,
            firm_name=firm_name,
            client_count_with_summaries=client_count,
        )
        for firm_id, firm_name, client_count in await list_global_client_report_counts(
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

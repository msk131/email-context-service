"""Summary coverage report services."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.time import utc_now
from app.models.users import User
from app.repositories.summaries import (
    count_firm_clients,
    count_firm_summaries,
    list_summary_counts_by_firm,
)
from app.schemas.summaries import (
    ReportFirmClientCount,
    ReportFirmSummaryRow,
    ReportGlobalResponse,
)


async def get_firm_summary_report(
    session: AsyncSession,
    *,
    current_user: User,
) -> ReportFirmClientCount:
    """Return summary coverage for the current user's firm."""
    count_with_summaries = await count_firm_summaries(session, current_user.firm_id)
    total_clients = await count_firm_clients(session, current_user.firm_id)
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

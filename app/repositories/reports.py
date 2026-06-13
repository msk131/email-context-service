"""Report read-model data access."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.clients import count_clients_by_firm
from app.repositories.email_summaries import (
    count_summaries_by_firm,
    list_summary_counts_by_firm,
)


async def get_firm_client_report_counts(
    session: AsyncSession,
    firm_id: int,
) -> tuple[int, int]:
    """Return generated-report count and total client count for one firm."""
    count_with_reports = await count_summaries_by_firm(session, firm_id)
    total_clients = await count_clients_by_firm(session, firm_id)
    return count_with_reports, total_clients


async def list_global_client_report_counts(
    session: AsyncSession,
) -> list[tuple[int, str, int]]:
    """Return generated-report counts grouped by firm."""
    return await list_summary_counts_by_firm(session)

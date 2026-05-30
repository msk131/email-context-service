"""Summary response mapping helpers."""

from app.models.clients import Client
from app.models.summaries import EmailSummary
from app.schemas.summaries import SummaryResponse, SummaryResult
from app.utils import decrypt_text


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

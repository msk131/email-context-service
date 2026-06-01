"""Summary cache read services."""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_summary_cache, set_summary_cache
from app.common.schemas import Role
from app.core.logging_config import get_logger
from app.models.users import User
from app.repositories.summaries import get_summary_record, load_client
from app.schemas.summaries import SummaryResponse
from app.services.clients import authorize_client_for_user
from app.services.summary_mapping import summary_response_from_record

logger = get_logger("services.summary_cache")


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

"""Firms API routes (HTTP layer).

Handles firm operations.
Calls: services.firms for business logic
Uses: models.firms (ORM), schemas.firms (validation)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.auth import Accountant
from app.services.auth import require_role
from app.services.firms import get_firm_service
from app.schemas.firms import FirmRead
from app.common.schemas import Role

router = APIRouter(prefix="/firms", tags=["firms"])


@router.get(
    "/{firm_id}",
    response_model=FirmRead,
    summary="Get firm details",
    description="Returns firm metadata for authenticated users.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        404: {"description": "Firm not found"},
    },
)
async def get_firm(
    firm_id: int,
    current_user: Accountant = Depends(require_role(Role.superuser, Role.firm_admin, Role.accountant)),
    session: AsyncSession = Depends(get_session),
) -> FirmRead:
    """Get firm details."""
    firm = await get_firm_service(session, firm_id)
    return firm

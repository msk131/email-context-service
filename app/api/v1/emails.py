"""Email API routes."""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role
from app.db.database import get_session
from app.models.auth import Accountant
from app.schemas.emails import EmailRead
from app.api.dependencies.auth import require_role
from app.services.emails import read_client_emails

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get(
    "/clients/{client_id}",
    response_model=list[EmailRead],
    summary="List recent client emails",
    description="Returns the most recent stored emails for a client, if the requester is authorized.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client not found"},
    },
)
async def get_client_emails(
    client_id: int = Path(..., ge=1),
    limit: int = Query(50, ge=1, le=200),
    current_user: Accountant = Depends(require_role(Role.accountant, Role.firm_admin, Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> list[EmailRead]:
    """List client emails."""
    return await read_client_emails(
        session, current_user=current_user, client_id=client_id, limit=limit
    )

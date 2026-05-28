"""Clients API routes (HTTP layer).

Handles client CRUD and access operations.
Calls: services.clients for business logic
Uses: models.clients (ORM), schemas.clients (validation)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.auth import Accountant
from app.services.auth import require_role
from app.services.clients import authorize_client_for_user
from app.repositories.clients import get_client_by_id
from app.schemas.clients import ClientRead
from app.common.schemas import Role

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get(
    "/{client_id}",
    response_model=ClientRead,
    summary="Get client details",
    description="Returns a client when the authenticated user can access the client's firm.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client not found"},
    },
)
async def get_client(
    client_id: int,
    current_user: Accountant = Depends(require_role(Role.superuser, Role.firm_admin, Role.accountant)),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    """Get client details. User must have access to this client."""
    client = await get_client_by_id(session, client_id)
    await authorize_client_for_user(current_user, client, current_user.role)
    return client

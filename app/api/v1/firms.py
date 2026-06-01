"""Firms API routes (HTTP layer).

Handles firm CRUD operations.
Calls: services.firms for business logic
Uses: models.firms (ORM), schemas.firms (validation)
"""

from fastapi import APIRouter, Depends, Path, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.users import User
from app.api.dependencies.auth import require_role
from app.services.firms import (
    create_firm_service,
    delete_firm_service,
    get_authorized_firm_service,
    list_firms_service,
    update_firm_service,
)
from app.schemas.firms import FirmCreate, FirmRead, FirmUpdate
from app.common.schemas import Role

router = APIRouter(prefix="/firms", tags=["firms"])


@router.get(
    "",
    response_model=list[FirmRead],
    summary="List firms",
    description="Lists all firms for superusers, or the current user's firm for firm-scoped users.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
    },
)
async def list_firms(
    current_user: User = Depends(
        require_role(Role.superuser, Role.firm_admin, Role.accountant)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[FirmRead]:
    """List firms visible to the current user."""
    return await list_firms_service(session, current_user)


@router.post(
    "",
    response_model=FirmRead,
    status_code=201,
    summary="Create a firm",
    description="Creates a new accounting firm. Superuser access is required.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        409: {"description": "Firm name already exists"},
        422: {"description": "Invalid request body"},
    },
)
async def create_firm(
    request: FirmCreate,
    current_user: User = Depends(require_role(Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> FirmRead:
    """Create a firm."""
    _ = current_user
    return await create_firm_service(session, name=request.name)


@router.get(
    "/{firm_id}",
    response_model=FirmRead,
    summary="Get firm details",
    description="Returns firm metadata if the authenticated user has access rights.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        404: {"description": "Firm not found"},
    },
)
async def get_firm(
    firm_id: int = Path(..., ge=1),
    current_user: User = Depends(
        require_role(Role.superuser, Role.firm_admin, Role.accountant)
    ),
    session: AsyncSession = Depends(get_session),
) -> FirmRead:
    """Get firm details."""
    return await get_authorized_firm_service(
        session,
        firm_id=firm_id,
        current_user=current_user,
    )


@router.patch(
    "/{firm_id}",
    response_model=FirmRead,
    summary="Update a firm",
    description="Updates firm metadata. Superusers can update any firm; firm admins can update their own firm.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot update this firm"},
        404: {"description": "Firm not found"},
        409: {"description": "Firm name already exists"},
        422: {"description": "Invalid request body"},
    },
)
async def update_firm(
    request: FirmUpdate,
    firm_id: int = Path(..., ge=1),
    current_user: User = Depends(require_role(Role.superuser, Role.firm_admin)),
    session: AsyncSession = Depends(get_session),
) -> FirmRead:
    """Update firm details."""
    return await update_firm_service(
        session,
        firm_id=firm_id,
        name=request.name,
        current_user=current_user,
    )


@router.delete(
    "/{firm_id}",
    status_code=204,
    summary="Delete a firm",
    description="Deletes a firm and its related users and clients. Superuser access is required.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        404: {"description": "Firm not found"},
    },
)
async def delete_firm(
    firm_id: int = Path(..., ge=1),
    current_user: User = Depends(require_role(Role.superuser)),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a firm."""
    _ = current_user
    await delete_firm_service(session, firm_id=firm_id)
    return Response(status_code=204)

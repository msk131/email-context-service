"""Clients API routes (HTTP layer).

Handles client CRUD and access operations.
Calls: services.clients for business logic
Uses: models.clients (ORM), schemas.clients (validation)
"""

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.auth import Accountant
from app.api.dependencies.auth import require_role
from app.services.clients import (
    create_client_service,
    delete_client_service,
    get_client_service,
    list_clients_service,
    update_client_service,
)
from app.schemas.clients import ClientCreate, ClientRead, ClientUpdate
from app.common.schemas import Role

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get(
    "",
    response_model=list[ClientRead],
    summary="List clients",
    description="Lists clients visible to the authenticated user. Superusers may filter by firm_id.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access the requested firm"},
    },
)
async def list_clients(
    firm_id: int | None = Query(default=None, ge=1),
    current_user: Accountant = Depends(
        require_role(Role.superuser, Role.firm_admin, Role.accountant)
    ),
    session: AsyncSession = Depends(get_session),
) -> list[ClientRead]:
    """List clients visible to the current user."""
    return await list_clients_service(
        session,
        current_user=current_user,
        firm_id=firm_id,
    )


@router.post(
    "",
    response_model=ClientRead,
    status_code=201,
    summary="Create a client",
    description="Creates a client for the authenticated user's firm, or a supplied firm_id for superusers.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot create clients for this firm"},
        404: {"description": "Firm not found"},
        409: {"description": "Client email already exists for this firm"},
        422: {"description": "Invalid request body"},
    },
)
async def create_client(
    request: ClientCreate,
    current_user: Accountant = Depends(
        require_role(Role.superuser, Role.firm_admin, Role.accountant)
    ),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    """Create a client."""
    return await create_client_service(
        session,
        name=request.name,
        external_email=str(request.external_email),
        firm_id=request.firm_id,
        current_user=current_user,
    )


@router.get(
    "/{client_id}",
    response_model=ClientRead,
    summary="Get client details",
    description="Returns client metadata if the authenticated user is authorized to access the client's firm.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot access this client"},
        404: {"description": "Client not found"},
    },
)
async def get_client(
    client_id: int = Path(..., ge=1),
    current_user: Accountant = Depends(
        require_role(Role.superuser, Role.firm_admin, Role.accountant)
    ),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    """Get client details. User must have access to this client."""
    return await get_client_service(
        session,
        client_id=client_id,
        current_user=current_user,
    )


@router.patch(
    "/{client_id}",
    response_model=ClientRead,
    summary="Update a client",
    description="Updates client metadata after firm-scoped authorization.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot update this client"},
        404: {"description": "Client or target firm not found"},
        409: {"description": "Client email already exists for this firm"},
        422: {"description": "Invalid request body"},
    },
)
async def update_client(
    request: ClientUpdate,
    client_id: int = Path(..., ge=1),
    current_user: Accountant = Depends(
        require_role(Role.superuser, Role.firm_admin, Role.accountant)
    ),
    session: AsyncSession = Depends(get_session),
) -> ClientRead:
    """Update client details."""
    return await update_client_service(
        session,
        client_id=client_id,
        name=request.name,
        external_email=str(request.external_email) if request.external_email else None,
        firm_id=request.firm_id,
        current_user=current_user,
    )


@router.delete(
    "/{client_id}",
    status_code=204,
    summary="Delete a client",
    description="Deletes a client after firm-scoped authorization.",
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "User cannot delete this client"},
        404: {"description": "Client not found"},
    },
)
async def delete_client(
    client_id: int = Path(..., ge=1),
    current_user: Accountant = Depends(
        require_role(Role.superuser, Role.firm_admin, Role.accountant)
    ),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Delete a client."""
    await delete_client_service(
        session,
        client_id=client_id,
        current_user=current_user,
    )
    return Response(status_code=204)

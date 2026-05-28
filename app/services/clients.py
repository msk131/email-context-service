"""Clients service - business logic for client operations."""
from app.models.clients import Client
from app.models.auth import Accountant
from app.common.exceptions import AccessDeniedError
from app.common.schemas import Role


async def authorize_client_for_user(user: Accountant, client: Client, role: Role) -> None:
    """Authorize user access to client (must be same firm or superuser).
    
    Raises AccessDeniedError if user cannot access this client.
    """
    if Role(role.value if hasattr(role, "value") else role) == Role.superuser:
        return
    if client.firm_id != user.firm_id:
        raise AccessDeniedError("Access denied for this client")

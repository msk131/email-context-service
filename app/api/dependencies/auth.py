"""Authentication and authorization dependencies."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role, TokenPayload
from app.core.setting import settings
from app.db.database import get_session
from app.models.auth import Accountant
from app.repositories.auth import get_accountant_by_id

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Accountant:
    """Get the current authenticated user from a JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        token_data = TokenPayload(**payload)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc
    user = await get_accountant_by_id(session, int(token_data.sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Accountant | None:
    """Return the current user when a valid token is supplied, otherwise None."""
    if credentials is None:
        return None
    return await get_current_user(credentials, session)


def require_role(*allowed_roles: Role):
    """Require one of the supplied roles for an endpoint."""
    async def role_dependency(user: Accountant = Depends(get_current_user)) -> Accountant:
        if Role(user.role.value) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_dependency

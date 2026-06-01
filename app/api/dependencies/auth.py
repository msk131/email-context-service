"""Authentication and authorization dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role, TokenPayload
from app.core.setting import settings
from app.db.database import get_session
from app.models.user import User
from app.repositories.users import get_user_by_id

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    """Get the current authenticated user from a JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        token_data = TokenPayload.model_validate(payload)
        user_id = int(token_data.sub)
    except (JWTError, ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc
    user = await get_user_by_id(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_role(*allowed_roles: Role):
    """Require one of the supplied roles for an endpoint."""

    async def role_dependency(
        user: User = Depends(get_current_user),
    ) -> User:
        if user.platform_role != Role.superuser and user.primary_membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not assigned to a firm",
            )
        if Role(user.role.value) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_dependency

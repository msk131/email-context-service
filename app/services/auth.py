"""Auth service - business logic for authentication."""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.auth import Accountant
from app.models.firms import Firm
from app.repositories.auth import count_accountants, get_accountant_by_email, get_accountant_by_id
from app.common.models import RoleEnum
from app.common.schemas import Role, TokenPayload

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)
BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password cannot be longer than 72 bytes",
        )
    return password_bytes


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a bcrypt hash."""
    try:
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > BCRYPT_MAX_BYTES:
            return False
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except ValueError:
        return False


async def get_db_session():
    from app.db.database import get_session

    async for session in get_session():
        yield session


async def authenticate_accountant(
    session: AsyncSession, email: str, password: str
) -> Accountant | None:
    """Authenticate accountant with email and password. Returns None if invalid."""
    user = await get_accountant_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def register_accountant(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    role: Role,
    firm_id: int | None = None,
    firm_name: str | None = None,
    current_user: Accountant | None = None,
) -> Accountant:
    """Register a user with bootstrap and admin-only rules."""
    existing = await get_accountant_by_email(session, email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user_count = await count_accountants(session)
    is_bootstrap = user_count == 0
    if is_bootstrap:
        if role != Role.superuser:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The first registered user must be a superuser",
            )
        firm = await get_or_create_firm(session, firm_id=firm_id, firm_name=firm_name or "Default Firm")
    else:
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication is required after the first user is registered",
            )
        current_role = Role(current_user.role.value)
        if current_role == Role.firm_admin:
            if role == Role.superuser:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Firm admins cannot create superusers",
                )
            firm = await get_or_create_firm(session, firm_id=current_user.firm_id)
        elif current_role == Role.superuser:
            firm = await get_or_create_firm(session, firm_id=firm_id, firm_name=firm_name)
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only firm admins and superusers can register users",
            )

    user = Accountant(
        firm_id=firm.id,
        email=email,
        password_hash=hash_password(password),
        role=RoleEnum(role.value),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_or_create_firm(
    session: AsyncSession, *, firm_id: int | None = None, firm_name: str | None = None
) -> Firm:
    """Resolve an existing firm or create one by name."""
    if firm_id is not None:
        firm = await session.get(Firm, firm_id)
        if not firm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Firm with id {firm_id} not found",
            )
        return firm
    if not firm_name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="firm_id or firm_name is required",
        )

    firm = (await session.execute(select(Firm).where(Firm.name == firm_name))).scalar_one_or_none()
    if firm:
        return firm
    firm = Firm(name=firm_name)
    session.add(firm)
    await session.flush()
    return firm


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token from payload data."""
    payload = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload.update({"exp": expire})
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Accountant:
    """Dependency: Get current authenticated user from JWT token."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        token_data = TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    user = await get_accountant_by_id(session, int(token_data.sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(optional_security)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Accountant | None:
    """Return the current user when a valid token is supplied, otherwise None."""
    if credentials is None:
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        token_data = TokenPayload(**payload)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    user = await get_accountant_by_id(session, int(token_data.sub))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_role(*allowed_roles: Role):
    """Dependency factory: Require specific role(s) for access."""
    async def role_dependency(user: Accountant = Depends(get_current_user)) -> Accountant:
        if Role(user.role.value) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user
    return role_dependency

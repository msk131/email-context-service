from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from jose import jwt

from app.api.dependencies import auth as auth_dependencies
from app.common.schemas import Role
from app.core.config import settings
from app.services.auth import (
    create_access_token,
    hash_password,
    hash_password_async,
    verify_password,
    verify_password_async,
)


def test_create_access_token_contains_role_and_expiry():
    token = create_access_token(
        {"sub": "1", "role": Role.accountant.value, "firm_id": 1},
        expires_delta=timedelta(minutes=5),
    )
    payload = jwt.decode(
        token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
    )

    assert payload["sub"] == "1"
    assert payload["role"] == Role.accountant.value
    assert payload["firm_id"] == 1
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


def test_hash_password_and_verify_password():
    password = "SuperSecret123"
    password_hash = hash_password(password)

    assert verify_password(password, password_hash)
    assert not verify_password("WrongPassword", password_hash)
    assert not verify_password("x" * 100, password_hash)


@pytest.mark.asyncio
async def test_async_password_helpers_match_sync_behavior():
    password = "SuperSecret123"
    password_hash = await hash_password_async(password)

    assert await verify_password_async(password, password_hash)
    assert not await verify_password_async("WrongPassword", password_hash)


@pytest.mark.asyncio
async def test_get_current_user_rejects_non_integer_subject():
    token = create_access_token(
        {"sub": "not-an-int", "role": Role.accountant.value, "firm_id": 1},
        expires_delta=timedelta(minutes=5),
    )

    with pytest.raises(HTTPException) as exc:
        await auth_dependencies.get_current_user(
            SimpleNamespace(credentials=token),
            session=SimpleNamespace(),
        )

    assert exc.value.status_code == 401

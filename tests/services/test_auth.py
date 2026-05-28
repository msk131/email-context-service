from datetime import datetime, timedelta, timezone

from jose import jwt

from app.common.schemas import Role
from app.core.config import settings
from app.services.auth import create_access_token, hash_password, verify_password


def test_create_access_token_contains_role_and_expiry():
    token = create_access_token({"sub": "1", "role": Role.accountant.value, "firm_id": 1}, expires_delta=timedelta(minutes=5))
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

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

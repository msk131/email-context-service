import pytest
from pydantic import ValidationError

from app.core.setting import Settings


def _required_settings(**overrides):
    values = {
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "JWT_SECRET_KEY": "test-secret-key",
        "ENCRYPTION_KEY_HEX": "0" * 64,
    }
    values.update(overrides)
    return values


def test_cors_origins_support_csv_values():
    settings = Settings(
        **_required_settings(
            CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:5173"
        )
    )

    assert settings.cors_allowed_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]


def test_cors_origins_reject_wildcard_with_credentials():
    with pytest.raises(ValidationError):
        Settings(**_required_settings(CORS_ALLOWED_ORIGINS="*"))

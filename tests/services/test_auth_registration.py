import pytest
from fastapi import HTTPException

from app.common.models import RoleEnum
from app.common.schemas import Role
from app.models.users import User
from app.models.firms import Firm
from app.services.auth import register_user


class DummySession:
    def __init__(self):
        self.added = None

    def add(self, obj):
        self.added = obj

    async def commit(self):
        pass

    async def refresh(self, instance):
        setattr(instance, "id", 1)


@pytest.mark.asyncio
async def test_register_additional_user_requires_auth(monkeypatch):
    async def fake_get_user_by_email(session, email):
        return None

    async def fake_count_users(session):
        return 1

    monkeypatch.setattr(
        "app.services.auth.get_user_by_email", fake_get_user_by_email
    )
    monkeypatch.setattr("app.services.auth.count_users", fake_count_users)

    session = DummySession()
    with pytest.raises(HTTPException) as exc_info:
        await register_user(
            session,
            email="new.user@example.org",
            password="Password123!",
            role=Role.accountant,
            firm_name="Open Firm",
            current_user=None,
        )

    assert exc_info.value.status_code == 401
    assert session.added is None


@pytest.mark.asyncio
async def test_bootstrap_superuser_can_register_without_firm(monkeypatch):
    async def fake_get_user_by_email(session, email):
        return None

    async def fake_count_users(session):
        return 0

    monkeypatch.setattr("app.services.auth.get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr("app.services.auth.count_users", fake_count_users)

    session = DummySession()
    user = await register_user(
        session,
        email="admin@example.org",
        password="Password123!",
        role=Role.superuser,
        current_user=None,
    )

    assert user.role == RoleEnum.superuser
    assert user.firm_id is None
    assert session.added is user


@pytest.mark.asyncio
async def test_register_additional_user_with_firm_admin(monkeypatch):
    async def fake_get_user_by_email(session, email):
        return None

    async def fake_count_users(session):
        return 1

    async def fake_get_or_create_firm(session, firm_id, firm_name=None):
        return Firm(id=firm_id, name="Admin Firm")

    monkeypatch.setattr(
        "app.services.auth.get_user_by_email", fake_get_user_by_email
    )
    monkeypatch.setattr("app.services.auth.count_users", fake_count_users)
    monkeypatch.setattr("app.services.auth.get_or_create_firm", fake_get_or_create_firm)

    session = DummySession()
    current_user = User(
        id=99,
        firm_id=7,
        email="admin@example.org",
        password_hash="hash",
        role=RoleEnum.firm_admin,
    )
    user = await register_user(
        session,
        email="new.user@example.org",
        password="Password123!",
        role=Role.accountant,
        firm_name="Ignored Firm",
        current_user=current_user,
    )

    assert user.email == "new.user@example.org"
    assert user.role == RoleEnum.accountant
    assert user.firm_id == 7
    assert user.platform_role is None
    assert len(user.firm_memberships) == 1
    assert user.firm_memberships[0].role == RoleEnum.accountant
    assert len(user.accountant_profiles) == 1
    assert user.accountant_profiles[0].firm_id == 7
    assert session.added is user

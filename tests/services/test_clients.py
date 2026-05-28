import pytest

from app.common.exceptions import AccessDeniedError
from app.common.models import RoleEnum
from app.common.schemas import Role
from app.models.auth import Accountant
from app.models.clients import Client
from app.services.clients import authorize_client_for_user


@pytest.mark.asyncio
async def test_authorize_client_for_superuser_allows_access():
    user = Accountant(firm_id=1, email="super@example.com", password_hash="hash", role=RoleEnum.superuser)
    client = Client(firm_id=99, name="Client", external_email="client@example.com")

    await authorize_client_for_user(user, client, Role.superuser)


@pytest.mark.asyncio
async def test_authorize_client_for_user_denies_when_firm_mismatch():
    user = Accountant(firm_id=1, email="user@example.com", password_hash="hash", role=RoleEnum.accountant)
    client = Client(firm_id=2, name="Client", external_email="client@example.com")

    with pytest.raises(AccessDeniedError):
        await authorize_client_for_user(user, client, Role.accountant)

import pytest

from app.db import database, session


@pytest.mark.asyncio
async def test_get_session_yields_async_session():
    async for sess in database.get_session():
        assert sess is not None
        assert hasattr(sess, "execute")
        break


def test_session_module_imports():
    assert session.async_session is not None

import asyncio

import pytest

from app.cache import get_summary_cache, set_summary_cache, invalidate_summary_cache


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test basic cache set/get operations."""
    client_id = 1
    payload = {"summary": "Test summary", "actors": ["John", "Jane"]}

    await set_summary_cache(client_id, payload)
    cached = await get_summary_cache(client_id)

    assert cached is not None
    assert cached["summary"] == "Test summary"
    assert cached["actors"] == ["John", "Jane"]


@pytest.mark.asyncio
async def test_cache_ttl_expiration(monkeypatch):
    """Test that cache expires after TTL."""
    # Override TTL to 1 second for testing
    from app.core.config import settings

    original_ttl = settings.summary_cache_ttl_seconds
    settings.summary_cache_ttl_seconds = 1

    client_id = 2
    payload = {"summary": "Expiring summary"}

    await set_summary_cache(client_id, payload)
    cached = await get_summary_cache(client_id)
    assert cached is not None

    # Wait for expiration
    await asyncio.sleep(1.1)
    cached = await get_summary_cache(client_id)
    assert cached is None

    # Restore original TTL
    settings.summary_cache_ttl_seconds = original_ttl


@pytest.mark.asyncio
async def test_cache_invalidate():
    """Test immediate cache invalidation."""
    client_id = 3
    payload = {"summary": "To be invalidated"}

    await set_summary_cache(client_id, payload)
    cached = await get_summary_cache(client_id)
    assert cached is not None

    await invalidate_summary_cache(client_id)
    cached = await get_summary_cache(client_id)
    assert cached is None


@pytest.mark.asyncio
async def test_cache_missing_key():
    """Test that missing keys return None."""
    cached = await get_summary_cache(999)
    assert cached is None

import pytest
import importlib

cache_module = importlib.import_module("app.cache.cache")


@pytest.mark.asyncio
async def test_direct_cache_module_functions():
    cache_module._cache_store.clear()

    client_id = 42
    payload = {"summary": "direct cache test"}

    await cache_module.set_summary_cache(client_id, payload)
    cached = await cache_module.get_summary_cache(client_id)

    assert cached == payload

    await cache_module.invalidate_summary_cache(client_id)
    assert await cache_module.get_summary_cache(client_id) is None


def test_get_cache_stats_counts_entries():
    cache_module._cache_store.clear()
    cache_module._cache_store["summary:1"] = ({"summary": "x"}, 0.0)

    stats = cache_module.get_cache_stats()

    assert stats["cached_summaries"] == 1
    assert stats["cache_size_bytes"] > 0

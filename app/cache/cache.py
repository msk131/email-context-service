import time
from typing import Optional

from app.core.config import settings

# In-memory cache with TTL support
_cache_store: dict[str, tuple[dict, float]] = {}
_cache_lock_time: dict[str, float] = {}


async def get_summary_cache(client_id: int) -> Optional[dict]:
    """Retrieve cached summary with TTL validation."""
    key = f"summary:{client_id}"
    if key not in _cache_store:
        return None

    payload, timestamp = _cache_store[key]
    elapsed = time.time() - timestamp

    if elapsed > settings.summary_cache_ttl_seconds:
        del _cache_store[key]
        return None

    return payload


async def set_summary_cache(client_id: int, payload: dict) -> None:
    """Store summary in LRU cache with TTL."""
    key = f"summary:{client_id}"
    _cache_store[key] = (payload, time.time())


async def invalidate_summary_cache(client_id: int) -> None:
    """Remove cached summary immediately."""
    key = f"summary:{client_id}"
    if key in _cache_store:
        del _cache_store[key]


def get_cache_stats() -> dict:
    """Return cache statistics for monitoring."""
    return {
        "cached_summaries": len(_cache_store),
        "cache_size_bytes": sum(len(str(v)) for v in _cache_store.values()),
    }

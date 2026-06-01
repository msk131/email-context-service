"""Backward-compatible cache module imports."""

from app.cache.lru import (
    _cache_store,
    get_cache_stats,
    get_summary_cache,
    invalidate_summary_cache,
    set_summary_cache,
)

__all__ = [
    "_cache_store",
    "get_cache_stats",
    "get_summary_cache",
    "set_summary_cache",
    "invalidate_summary_cache",
]

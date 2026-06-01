import json
import time
from collections.abc import Mapping
from collections import OrderedDict
from typing import Any

from app.core import settings

try:
    import orjson
except ModuleNotFoundError:  # pragma: no cover - production dependency
    orjson = None

try:
    from redis.asyncio import Redis
    from redis.exceptions import RedisError
except ModuleNotFoundError:  # pragma: no cover - production dependency
    Redis = None

    class RedisError(Exception):
        """Fallback Redis exception when redis-py is not installed."""


JsonObject = dict[str, Any]

# Local fallback keeps development and unit tests usable without a Redis daemon.
_cache_store: OrderedDict[str, tuple[JsonObject, float]] = OrderedDict()
_redis_client: Any | None = None
_redis_disabled = False


def _cache_key(client_id: int) -> str:
    return f"summary:{client_id}"


def _dumps(payload: Mapping[str, Any]) -> bytes:
    if orjson is not None:
        return orjson.dumps(payload)
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _loads(payload: bytes | str) -> JsonObject:
    if orjson is not None:
        return dict(orjson.loads(payload))
    raw = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    return dict(json.loads(raw))


def _redis() -> Any | None:
    global _redis_client
    if _redis_disabled or Redis is None or not settings.redis_url:
        return None
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=False,
            socket_connect_timeout=0.05,
            socket_timeout=0.05,
        )
    return _redis_client


async def _redis_get(key: str) -> JsonObject | None:
    global _redis_disabled
    client = _redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except RedisError:
        _redis_disabled = True
        return None
    return _loads(raw) if raw else None


async def _redis_set(key: str, payload: Mapping[str, Any]) -> bool:
    global _redis_disabled
    client = _redis()
    if client is None:
        return False
    try:
        await client.setex(key, settings.summary_cache_ttl_seconds, _dumps(payload))
        return True
    except RedisError:
        _redis_disabled = True
        return False


async def _redis_delete(key: str) -> bool:
    global _redis_disabled
    client = _redis()
    if client is None:
        return False
    try:
        await client.delete(key)
        return True
    except RedisError:
        _redis_disabled = True
        return False


async def get_summary_cache(client_id: int) -> JsonObject | None:
    """Retrieve cached summary with TTL validation."""
    key = _cache_key(client_id)
    redis_payload = await _redis_get(key)
    if redis_payload is not None:
        return redis_payload

    if key not in _cache_store:
        return None

    payload, timestamp = _cache_store[key]
    elapsed = time.time() - timestamp

    if elapsed > settings.summary_cache_ttl_seconds:
        del _cache_store[key]
        return None

    _cache_store.move_to_end(key)
    return payload


async def set_summary_cache(client_id: int, payload: Mapping[str, Any]) -> None:
    """Store summary in LRU cache with TTL."""
    key = _cache_key(client_id)
    if await _redis_set(key, payload):
        return

    _cache_store[key] = (dict(payload), time.time())
    _cache_store.move_to_end(key)
    while len(_cache_store) > settings.summary_cache_max_items:
        _cache_store.popitem(last=False)


async def invalidate_summary_cache(client_id: int) -> None:
    """Remove cached summary immediately."""
    key = _cache_key(client_id)
    await _redis_delete(key)
    if key in _cache_store:
        del _cache_store[key]


def get_cache_stats() -> JsonObject:
    """Return cache statistics for monitoring."""
    return {
        "cached_summaries": len(_cache_store),
        "cache_size_bytes": sum(len(str(v)) for v in _cache_store.values()),
    }

# Caching And Serialization

## Tools

- `Redis`
- `orjson`
- Local in-process fallback cache

## Purpose

Redis is the production cache for generated report reads and vector/search
responses. `orjson` provides faster JSON serialization for cache payloads. The
local fallback keeps tests and development working when Redis is unavailable.

## Where It Lives

- Cache helpers: `app/cache/lru.py`
- Public cache exports: `app/cache/__init__.py`
- Search cache usage: `app/services/email_search.py`
- Report cache usage: `app/services/summaries.py`

## Design Notes

- Redis is preferred when `REDIS_URL` is configured.
- Cache keys hash sensitive query parameters instead of storing raw query text.
- Database tables remain the source of truth; cache entries are derived data.

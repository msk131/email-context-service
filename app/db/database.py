from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.setting import settings


def _engine_options() -> dict:
    """Return production pool options, skipping unsupported options for SQLite."""
    options = {"echo": False, "future": True}
    if not settings.database_url.startswith("sqlite"):
        options.update(
            {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_timeout": settings.database_pool_timeout_seconds,
                "pool_recycle": settings.database_pool_recycle_seconds,
                "pool_pre_ping": True,
            }
        )
    return options


engine = create_async_engine(settings.database_url, **_engine_options())
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

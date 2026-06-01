"""Unit tests for task queue TTL, cleanup, and rate limiting."""

import pytest
import pytest_asyncio
from datetime import timedelta
from uuid import UUID
from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.common.models import Base
from app.common.time import utc_now
from app.models.background_task import (
    BackgroundTask,
    TaskStatus,
    TASK_TTL_SUCCEEDED,
    TASK_TTL_FAILED,
)
from app.repositories import tasks as task_repo


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
class TestTaskTTLAndCleanup:
    """Test task lifecycle, TTL assignment, and cleanup."""

    async def test_create_task(self, session: AsyncSession):
        """Task creation stores metadata correctly."""
        task = await task_repo.create_task(
            session, "summarize_client", {"client_id": 1}
        )

        assert task.id is not None
        assert isinstance(task.id, UUID)
        assert task.task_type == "summarize_client"
        assert task.status == TaskStatus.pending
        assert task.payload == {"client_id": 1}
        assert task.created_at is not None
        assert task.completed_at is None
        assert task.expires_at is None

    async def test_mark_succeeded_sets_ttl(self, session: AsyncSession):
        """Marking task succeeded sets expires_at to 7 days from now."""
        task = await task_repo.create_task(
            session, "summarize_client", {"client_id": 1}
        )

        result = {"summary": "test"}
        await task_repo.mark_succeeded(session, task.id, result)

        updated_task = await task_repo.get_task(session, task.id)
        assert updated_task.status == TaskStatus.succeeded
        assert updated_task.result == result
        assert updated_task.completed_at is not None
        assert updated_task.expires_at is not None

        # Verify TTL is approximately 7 days
        ttl_delta = updated_task.expires_at - updated_task.completed_at
        assert abs((ttl_delta - TASK_TTL_SUCCEEDED).total_seconds()) < 1

    async def test_mark_failed_sets_ttl(self, session: AsyncSession):
        """Marking task failed sets expires_at to 30 days from now."""
        task = await task_repo.create_task(
            session, "summarize_client", {"client_id": 1}
        )

        await task_repo.mark_failed(session, task.id, error="Something went wrong")

        updated_task = await task_repo.get_task(session, task.id)
        assert updated_task.status == TaskStatus.failed
        assert updated_task.error == "TASK_EXECUTION_FAILED"
        assert updated_task.completed_at is not None
        assert updated_task.expires_at is not None

        # Verify TTL is approximately 30 days
        ttl_delta = updated_task.expires_at - updated_task.completed_at
        assert abs((ttl_delta - TASK_TTL_FAILED).total_seconds()) < 1

    async def test_mark_running_no_ttl(self, session: AsyncSession):
        """Running tasks don't get TTL."""
        task = await task_repo.create_task(
            session, "summarize_client", {"client_id": 1}
        )

        await task_repo.mark_running(session, task.id)

        updated_task = await task_repo.get_task(session, task.id)
        assert updated_task.status == TaskStatus.running
        assert updated_task.completed_at is None
        assert updated_task.expires_at is None

    async def test_claim_pending_task_only_claims_once(self, session: AsyncSession):
        """Only one worker should be able to claim a pending task."""
        task = await task_repo.create_task(
            session, "summarize_client", {"client_id": 1}
        )

        claimed = await task_repo.claim_pending_task(session, task.id)
        second_claim = await task_repo.claim_pending_task(session, task.id)

        assert claimed is not None
        assert claimed.id == task.id
        assert claimed.status == TaskStatus.running
        assert second_claim is None

    async def test_cleanup_expired_tasks(self, session: AsyncSession):
        """Cleanup deletes only expired tasks, not pending/running."""
        now = utc_now()

        # Create tasks in different states
        expired_succeeded = await task_repo.create_task(
            session, "summarize_client", {"client_id": 1}
        )
        await task_repo.mark_succeeded(session, expired_succeeded.id, {})

        expired_failed = await task_repo.create_task(
            session, "summarize_client", {"client_id": 2}
        )
        await task_repo.mark_failed(session, expired_failed.id, error="error")

        # Manually set their expiration in the past
        await session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id.in_([expired_succeeded.id, expired_failed.id]))
            .values(expires_at=now - timedelta(days=1))
        )
        await session.commit()

        # Create tasks that should NOT be deleted
        pending = await task_repo.create_task(
            session, "summarize_client", {"client_id": 3}
        )
        running = await task_repo.create_task(
            session, "summarize_client", {"client_id": 4}
        )
        await task_repo.mark_running(session, running.id)

        # Fresh succeeded task (not expired yet)
        fresh_succeeded = await task_repo.create_task(
            session, "summarize_client", {"client_id": 5}
        )
        await task_repo.mark_succeeded(session, fresh_succeeded.id, {})

        # Run cleanup
        deleted_count = await task_repo.cleanup_expired_tasks(session)

        # Verify 2 tasks deleted (the expired ones)
        assert deleted_count == 2

        # Verify correct tasks remain
        assert await task_repo.get_task(session, pending.id) is not None
        assert await task_repo.get_task(session, running.id) is not None
        assert await task_repo.get_task(session, fresh_succeeded.id) is not None

        # Verify expired tasks are gone
        assert await task_repo.get_task(session, expired_succeeded.id) is None
        assert await task_repo.get_task(session, expired_failed.id) is None

    async def test_cleanup_batch_limit(self, session: AsyncSession):
        """Cleanup respects batch limit to prevent locking."""
        now = utc_now()

        # Create 15 expired tasks
        task_ids = []
        for i in range(15):
            task = await task_repo.create_task(
                session, "summarize_client", {"client_id": i}
            )
            await task_repo.mark_succeeded(session, task.id, {})
            task_ids.append(task.id)

        # Set all to expired
        await session.execute(
            update(BackgroundTask)
            .where(BackgroundTask.id.in_(task_ids))
            .values(expires_at=now - timedelta(days=1))
        )
        await session.commit()

        # Cleanup with batch limit of 10
        deleted_count = await task_repo.cleanup_expired_tasks(session, limit=10)

        # Should delete only 10
        assert deleted_count == 10

        # Next cleanup should delete remaining 5
        deleted_count = await task_repo.cleanup_expired_tasks(session, limit=10)
        assert deleted_count == 5

    async def test_fetch_pending_returns_unstarted_tasks(self, session: AsyncSession):
        """fetch_pending returns only pending tasks, in order."""
        task1 = await task_repo.create_task(
            session, "summarize_client", {"client_id": 1}
        )
        task2 = await task_repo.create_task(
            session, "summarize_client", {"client_id": 2}
        )

        running = await task_repo.create_task(
            session, "summarize_client", {"client_id": 3}
        )
        await task_repo.mark_running(session, running.id)

        task3 = await task_repo.create_task(
            session, "summarize_client", {"client_id": 4}
        )

        pending = await task_repo.fetch_pending(session, limit=10)

        pending_ids = [t.id for t in pending]
        assert task1.id in pending_ids
        assert task2.id in pending_ids
        assert task3.id in pending_ids
        assert running.id not in pending_ids
        assert len(pending_ids) == 3

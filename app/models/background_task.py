"""Background task ORM model."""

from datetime import timedelta
from enum import Enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, JSON, String, Text, Uuid

from app.common.models import Base
from app.common.time import utc_now


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


TASK_TTL_SUCCEEDED = timedelta(days=7)
TASK_TTL_FAILED = timedelta(days=30)


class BackgroundTask(Base):
    """DB-backed background task record."""

    __tablename__ = "background_tasks"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    task_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(SAEnum(TaskStatus), nullable=False, default=TaskStatus.pending)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)

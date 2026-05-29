from datetime import timedelta
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SAEnum, Integer, JSON, String, Text

from app.common.time import utc_now
from app.common.models import Base


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


# Task TTL Configuration
TASK_TTL_SUCCEEDED = timedelta(days=7)  # Keep succeeded tasks for 7 days
TASK_TTL_FAILED = timedelta(days=30)  # Keep failed tasks for 30 days


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id = Column(Integer, primary_key=True)
    task_type = Column(String(64), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(SAEnum(TaskStatus), nullable=False, default=TaskStatus.pending)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)  # Set when task succeeds or fails
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)  # Set when task completes, used for cleanup

"""Summarization log ORM model."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer

from app.common.models import Base


class SummarizationLog(Base):
    """Log of summarization operations."""

    __tablename__ = "summarization_logs"
    __table_args__ = (
        Index("ix_summarization_logs_client_completed", "client_id", "completed_at"),
    )

    id = Column(Integer, primary_key=True)
    client_id = Column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    email_count = Column(Integer, nullable=False)
    token_in = Column(Integer, nullable=False)
    token_out = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)

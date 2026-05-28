"""Summaries domain ORM models (database layer)."""

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.common.models import Base, EmailDirection


class Email(Base):
    """Email message model."""
    __tablename__ = "emails"
    __table_args__ = (
        Index("ix_emails_client_sent_at", "client_id", "sent_at"),
        Index("ix_emails_subject", "subject"),
        Index("ix_emails_sender_email", "sender_email"),
    )

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    sender_accountant_id = Column(Integer, ForeignKey("accountants.id", ondelete="SET NULL"), nullable=True)
    sender_email = Column(String(255), nullable=False)
    recipients = Column(JSON, nullable=False)
    subject = Column(String(512), nullable=False)
    body = Column(Text, nullable=False)
    direction = Column(Enum(EmailDirection), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    client = relationship("Client", back_populates="emails")


class EmailSummary(Base):
    """Cached email summary for a client."""
    __tablename__ = "email_summaries"
    __table_args__ = (UniqueConstraint("client_id", name="uq_email_summary_client"),)

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True)
    summary_encrypted = Column(Text, nullable=False)
    actors = Column(JSON, nullable=False, default=list)
    concluded_discussions = Column(JSON, nullable=False, default=list)
    open_action_items = Column(JSON, nullable=False, default=list)
    email_count_analyzed = Column(Integer, nullable=False, default=0)
    token_in = Column(Integer, nullable=False, default=0)
    token_out = Column(Integer, nullable=False, default=0)
    refreshed_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    client = relationship("Client", back_populates="summary")


class SummarizationLog(Base):
    """Log of summarization operations."""
    __tablename__ = "summarization_logs"
    __table_args__ = (Index("ix_summarization_logs_client_completed", "client_id", "completed_at"),)

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    email_count = Column(Integer, nullable=False)
    token_in = Column(Integer, nullable=False)
    token_out = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)

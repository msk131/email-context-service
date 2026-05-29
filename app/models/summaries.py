"""Summaries domain ORM models (database layer)."""

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.common.models import Base, EmailDirection


class Email(Base):
    """Email message model (Microsoft Graph API format)."""
    __tablename__ = "emails"
    __table_args__ = (
        Index("ix_emails_client_sent_at", "client_id", "sent_at"),
        Index("ix_emails_subject", "subject"),
        Index("ix_emails_sender_address", "sender_address"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    sender_accountant_id = Column(Integer, ForeignKey("accountants.id", ondelete="SET NULL"), nullable=True)
    
    # Sender: {address, name}
    sender = Column(JSON, nullable=False)
    sender_address = Column(String(255), nullable=False)  # Denormalized for indexing
    
    # Recipients: {to_recipients, cc_recipients, bcc_recipients} - each is list of {address, name}
    to_recipients = Column(JSON, nullable=False, default=list)
    cc_recipients = Column(JSON, nullable=False, default=list)
    bcc_recipients = Column(JSON, nullable=False, default=list)
    
    subject = Column(String(512), nullable=False)
    
    # Body: {contentType, content}
    body = Column(JSON, nullable=False)
    
    is_read = Column(Boolean, nullable=False, default=False)
    direction = Column(Enum(EmailDirection), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    client = relationship("Client", back_populates="emails")

    @property
    def sender_email(self) -> str:
        """Return the sender address from the stored Microsoft Graph shape."""
        return self.sender_address

    @sender_email.setter
    def sender_email(self, value: str) -> None:
        self.sender_address = value
        if not self.sender:
            self.sender = {"emailAddress": {"address": value}}

    @property
    def recipients(self) -> list[str]:
        """Return all recipient email addresses from the stored Graph recipients."""
        recipients = []
        all_recipients = (
            (self.to_recipients or [])
            + (self.cc_recipients or [])
            + (self.bcc_recipients or [])
        )
        for recipient in all_recipients:
            email_address = recipient.get("emailAddress") or {}
            address = email_address.get("address")
            if address:
                recipients.append(address)
        return recipients

    @recipients.setter
    def recipients(self, values: list[str]) -> None:
        self.to_recipients = [
            {"emailAddress": {"address": address}} for address in (values or [])
        ]
        self.cc_recipients = []
        self.bcc_recipients = []

    @property
    def body_text(self) -> str:
        """Return searchable/summarizable body content from the Graph body."""
        if isinstance(self.body, str):
            return self.body
        return (self.body or {}).get("content", "")


class EmailSummary(Base):
    """Cached email summary for a client."""
    __tablename__ = "email_summaries"
    __table_args__ = (
        UniqueConstraint("client_id", name="uq_email_summary_client"),
    )

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    summary_encrypted = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # Store embedding as JSON list of floats
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

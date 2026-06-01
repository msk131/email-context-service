"""Email summary ORM model."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.common.models import Base


class EmailSummary(Base):
    """Cached email summary for a client."""

    __tablename__ = "email_summaries"
    __table_args__ = (UniqueConstraint("client_id", name="uq_email_summary_client"),)

    id = Column(Integer, primary_key=True)
    client_id = Column(
        Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    summary_encrypted = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)
    actors = Column(JSON, nullable=False, default=list)
    concluded_discussions = Column(JSON, nullable=False, default=list)
    open_action_items = Column(JSON, nullable=False, default=list)
    email_count_analyzed = Column(Integer, nullable=False, default=0)
    token_in = Column(Integer, nullable=False, default=0)
    token_out = Column(Integer, nullable=False, default=0)
    refreshed_at = Column(DateTime(timezone=True), nullable=False)

    client = relationship("Client", back_populates="summary")

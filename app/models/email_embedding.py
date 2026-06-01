"""Email embedding ORM model for pgvector fallback indexing."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON

from app.common.models import Base
from app.common.time import utc_now


class EmailEmbedding(Base):
    """Embedding row associated with one email."""

    __tablename__ = "email_embeddings"

    email_id = Column(
        Integer, ForeignKey("emails.id", ondelete="CASCADE"), primary_key=True
    )
    embedding = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

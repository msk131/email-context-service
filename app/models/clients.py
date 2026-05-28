"""Clients domain ORM model (database layer)."""
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.common.models import Base


class Client(Base):
    """Client (customer) model."""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    firm_id = Column(Integer, ForeignKey("firms.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    external_email = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    firm = relationship("Firm", back_populates="clients")
    emails = relationship("Email", back_populates="client", cascade="all, delete-orphan")
    summary = relationship("EmailSummary", uselist=False, back_populates="client", cascade="all, delete-orphan")

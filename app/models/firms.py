"""Firms domain ORM model (database layer)."""

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.common.time import utc_now
from app.common.models import Base


class Firm(Base):
    """Firm (organization/company) model."""
    __tablename__ = "firms"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    accountants = relationship("Accountant", back_populates="firm", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="firm", cascade="all, delete-orphan")

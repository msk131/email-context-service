"""Client ORM model."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.common.models import Base
from app.common.time import utc_now


class Client(Base):
    """Client (customer) model."""

    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_firm_id", "firm_id"),
        UniqueConstraint(
            "firm_id", "external_email", name="uq_clients_firm_external_email"
        ),
    )

    id = Column(Integer, primary_key=True)
    firm_id = Column(
        Integer, ForeignKey("firms.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(255), nullable=False)
    external_email = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    firm = relationship("Firm", back_populates="clients")
    emails = relationship(
        "Email", back_populates="client", cascade="all, delete-orphan"
    )
    summary = relationship(
        "EmailSummary",
        uselist=False,
        back_populates="client",
        cascade="all, delete-orphan",
    )

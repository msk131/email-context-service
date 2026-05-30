"""Auth domain ORM model (database layer)."""

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.common.time import utc_now
from app.common.models import Base, RoleEnum


class Accountant(Base):
    """Accountant user model (superuser, firm_admin, or accountant)."""

    __tablename__ = "accountants"

    id = Column(Integer, primary_key=True)
    firm_id = Column(
        Integer, ForeignKey("firms.id", ondelete="CASCADE"), nullable=False
    )
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    firm = relationship("Firm", back_populates="accountants")

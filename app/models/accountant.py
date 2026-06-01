"""Accountant ORM model."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.common.models import Base
from app.common.time import utc_now


class Accountant(Base):
    """Accountant business profile tied to a user's single firm membership."""

    __tablename__ = "accountants"
    __table_args__ = (
        UniqueConstraint("user_id", "firm_id", name="uq_accountants_user_firm"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    firm_id = Column(Integer, ForeignKey("firms.id", ondelete="CASCADE"), nullable=False)
    membership_id = Column(
        Integer,
        ForeignKey("firm_memberships.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    display_name = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="accountant_profiles")
    firm = relationship("Firm", back_populates="accountants")
    membership = relationship("FirmMembership", back_populates="accountant_profile")

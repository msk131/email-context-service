"""Firm membership ORM model."""

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.common.models import Base, RoleEnum
from app.common.time import utc_now


class FirmMembership(Base):
    """A user's single firm assignment and role."""

    __tablename__ = "firm_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_firm_membership_user"),
        UniqueConstraint("user_id", "firm_id", name="uq_firm_membership_user_firm"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    firm_id = Column(
        Integer, ForeignKey("firms.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(Enum(RoleEnum), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="firm_memberships")
    firm = relationship("Firm", back_populates="memberships")
    accountant_profile = relationship(
        "Accountant",
        back_populates="membership",
        uselist=False,
        cascade="all, delete-orphan",
    )

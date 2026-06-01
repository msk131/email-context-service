"""User and firm membership ORM models."""

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.common.time import utc_now
from app.common.models import Base, RoleEnum


class User(Base):
    """Authenticated login identity."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    platform_role = Column(Enum(RoleEnum), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    firm_memberships = relationship(
        "FirmMembership", back_populates="user", cascade="all, delete-orphan"
    )
    accountant_profiles = relationship(
        "Accountant", back_populates="user", cascade="all, delete-orphan"
    )
    sent_emails = relationship("Email", back_populates="sender_user")

    @property
    def primary_membership(self) -> "FirmMembership | None":
        """Return the first firm membership for compatibility with single-firm flows."""
        return self.firm_memberships[0] if self.firm_memberships else None

    @property
    def role(self) -> RoleEnum:
        """Return the effective role used by existing authorization code."""
        if self.platform_role == RoleEnum.superuser:
            return RoleEnum.superuser
        membership = self.primary_membership
        return membership.role if membership else RoleEnum.accountant

    @role.setter
    def role(self, value: RoleEnum | str) -> None:
        role = RoleEnum(value)
        if role == RoleEnum.superuser:
            self.platform_role = RoleEnum.superuser
            return
        self.platform_role = None
        self._set_primary_membership_role(role)

    @property
    def firm_id(self) -> int | None:
        """Return the active firm id for single-firm service flows."""
        membership = self.primary_membership
        return membership.firm_id if membership else None

    @firm_id.setter
    def firm_id(self, value: int | None) -> None:
        if value is None:
            return
        role = self.role if self.platform_role != RoleEnum.superuser else RoleEnum.accountant
        self._set_primary_membership(value, role)

    def _set_primary_membership_role(self, role: RoleEnum) -> None:
        membership = self.primary_membership
        if membership:
            membership.role = role
            return
        firm_id = getattr(self, "_pending_firm_id", None)
        if firm_id is not None:
            self._set_primary_membership(firm_id, role)

    def _set_primary_membership(self, firm_id: int, role: RoleEnum) -> None:
        self._pending_firm_id = firm_id
        membership = self.primary_membership
        if membership:
            membership.firm_id = firm_id
            membership.role = role
            return
        self.firm_memberships.append(FirmMembership(firm_id=firm_id, role=role))


class FirmMembership(Base):
    """A user's role within a firm."""

    __tablename__ = "firm_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "firm_id", name="uq_firm_membership_user_firm"),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    firm_id = Column(Integer, ForeignKey("firms.id", ondelete="CASCADE"), nullable=False)
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

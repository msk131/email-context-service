"""Shared database models (Enums and Base)."""
import enum
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RoleEnum(str, enum.Enum):
    """User roles in the system."""
    superuser = "superuser"
    firm_admin = "firm_admin"
    accountant = "accountant"


class EmailDirection(str, enum.Enum):
    """Email direction classification."""
    inbound = "inbound"
    outbound = "outbound"

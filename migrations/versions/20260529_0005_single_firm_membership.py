"""enforce single firm membership per user

Revision ID: 20260529_0005
Revises: 20260529_0004
Create Date: 2026-05-29
"""
from alembic import op


revision = "20260529_0005"
down_revision = "20260529_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_unique_constraint(
            "uq_firm_membership_user",
            "firm_memberships",
            ["user_id"],
        )
        return

    with op.batch_alter_table("firm_memberships") as batch_op:
        batch_op.create_unique_constraint("uq_firm_membership_user", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(
            "uq_firm_membership_user",
            "firm_memberships",
            type_="unique",
        )
        return

    with op.batch_alter_table("firm_memberships") as batch_op:
        batch_op.drop_constraint("uq_firm_membership_user", type_="unique")

"""add email captured_at timestamp

Revision ID: 20260529_0004
Revises: 20260529_0003
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260529_0004"
down_revision = "20260529_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            ALTER TABLE emails
            ADD COLUMN IF NOT EXISTS captured_at TIMESTAMP WITH TIME ZONE
            """
        )
        op.execute("UPDATE emails SET captured_at = COALESCE(captured_at, sent_at)")
        op.execute("ALTER TABLE emails ALTER COLUMN captured_at SET NOT NULL")
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_emails_client_captured_at
            ON emails (client_id, captured_at)
            """
        )
        return

    with op.batch_alter_table("emails") as batch_op:
        batch_op.add_column(sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE emails SET captured_at = sent_at WHERE captured_at IS NULL")

    with op.batch_alter_table("emails") as batch_op:
        batch_op.alter_column("captured_at", nullable=False)
        batch_op.create_index("ix_emails_client_captured_at", ["client_id", "captured_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_emails_client_captured_at")
        op.execute("ALTER TABLE emails DROP COLUMN IF EXISTS captured_at")
        return

    with op.batch_alter_table("emails") as batch_op:
        batch_op.drop_index("ix_emails_client_captured_at")
        batch_op.drop_column("captured_at")

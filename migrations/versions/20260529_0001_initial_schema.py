"""initial schema

Revision ID: 20260529_0001
Revises:
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260529_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "firms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "background_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "succeeded", "failed", name="taskstatus"),
            nullable=False,
        ),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_background_tasks_expires_at"),
        "background_tasks",
        ["expires_at"],
        unique=False,
    )
    op.create_table(
        "accountants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("firm_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("superuser", "firm_admin", "accountant", name="roleenum"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("firm_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("external_email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["firm_id"], ["firms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "firm_id",
            "external_email",
            name="uq_clients_firm_external_email",
        ),
    )
    op.create_index("ix_clients_firm_id", "clients", ["firm_id"], unique=False)
    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("sender_accountant_id", sa.Integer(), nullable=True),
        sa.Column("sender", sa.JSON(), nullable=False),
        sa.Column("sender_address", sa.String(length=255), nullable=False),
        sa.Column("to_recipients", sa.JSON(), nullable=False),
        sa.Column("cc_recipients", sa.JSON(), nullable=False),
        sa.Column("bcc_recipients", sa.JSON(), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column(
            "direction",
            sa.Enum("inbound", "outbound", name="emaildirection"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["sender_accountant_id"],
            ["accountants.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_emails_client_sent_at", "emails", ["client_id", "sent_at"])
    op.create_index("ix_emails_sender_address", "emails", ["sender_address"])
    op.create_index("ix_emails_subject", "emails", ["subject"])
    op.create_table(
        "email_summaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("summary_encrypted", sa.Text(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("actors", sa.JSON(), nullable=False),
        sa.Column("concluded_discussions", sa.JSON(), nullable=False),
        sa.Column("open_action_items", sa.JSON(), nullable=False),
        sa.Column("email_count_analyzed", sa.Integer(), nullable=False),
        sa.Column("token_in", sa.Integer(), nullable=False),
        sa.Column("token_out", sa.Integer(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", name="uq_email_summary_client"),
    )
    op.create_table(
        "summarization_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("email_count", sa.Integer(), nullable=False),
        sa.Column("token_in", sa.Integer(), nullable=False),
        sa.Column("token_out", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_summarization_logs_client_completed",
        "summarization_logs",
        ["client_id", "completed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_summarization_logs_client_completed", table_name="summarization_logs")
    op.drop_table("summarization_logs")
    op.drop_table("email_summaries")
    op.drop_index("ix_emails_subject", table_name="emails")
    op.drop_index("ix_emails_sender_address", table_name="emails")
    op.drop_index("ix_emails_client_sent_at", table_name="emails")
    op.drop_table("emails")
    op.drop_index("ix_clients_firm_id", table_name="clients")
    op.drop_table("clients")
    op.drop_table("accountants")
    op.drop_index(op.f("ix_background_tasks_expires_at"), table_name="background_tasks")
    op.drop_table("background_tasks")
    op.drop_table("firms")

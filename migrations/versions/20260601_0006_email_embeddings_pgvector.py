"""add pgvector email embeddings fallback

Revision ID: 20260601_0006
Revises: 20260529_0005
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0006"
down_revision = "20260529_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.create_table(
            "email_embeddings",
            sa.Column(
                "email_id",
                sa.Integer(),
                sa.ForeignKey("emails.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("embedding", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.execute("ALTER TABLE email_embeddings ALTER COLUMN embedding TYPE vector(384) USING embedding::vector")
        op.execute(
            "CREATE INDEX ix_email_embeddings_vector ON email_embeddings "
            "USING ivfflat (embedding vector_cosine_ops)"
        )
        return

    op.create_table(
        "email_embeddings",
        sa.Column(
            "email_id",
            sa.Integer(),
            sa.ForeignKey("emails.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("email_embeddings")

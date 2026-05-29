"""convert email is_read to boolean

Revision ID: 20260529_0002
Revises: 20260529_0001
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260529_0002"
down_revision = "20260529_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'emails'
                      AND column_name = 'is_read'
                      AND data_type IN ('integer', 'smallint', 'bigint')
                ) THEN
                    ALTER TABLE emails
                    ALTER COLUMN is_read TYPE BOOLEAN
                    USING (is_read <> 0);
                END IF;
            END $$;
            """
        )
        return

    with op.batch_alter_table("emails") as batch_op:
        batch_op.alter_column(
            "is_read",
            existing_type=sa.Integer(),
            type_=sa.Boolean(),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name = 'emails'
                      AND column_name = 'is_read'
                      AND data_type = 'boolean'
                ) THEN
                    ALTER TABLE emails
                    ALTER COLUMN is_read TYPE INTEGER
                    USING CASE WHEN is_read THEN 1 ELSE 0 END;
                END IF;
            END $$;
            """
        )
        return

    with op.batch_alter_table("emails") as batch_op:
        batch_op.alter_column(
            "is_read",
            existing_type=sa.Boolean(),
            type_=sa.Integer(),
            existing_nullable=False,
        )

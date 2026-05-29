"""convert background task id to uuid

Revision ID: 20260529_0003
Revises: 20260529_0002
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260529_0003"
down_revision = "20260529_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        op.execute("ALTER TABLE background_tasks ADD COLUMN uuid_id UUID")
        op.execute("UPDATE background_tasks SET uuid_id = gen_random_uuid()")
        op.execute("ALTER TABLE background_tasks ALTER COLUMN uuid_id SET NOT NULL")
        op.execute("ALTER TABLE background_tasks DROP CONSTRAINT background_tasks_pkey")
        op.execute("ALTER TABLE background_tasks DROP COLUMN id")
        op.execute("ALTER TABLE background_tasks RENAME COLUMN uuid_id TO id")
        op.execute("ALTER TABLE background_tasks ADD PRIMARY KEY (id)")
        return

    with op.batch_alter_table("background_tasks") as batch_op:
        batch_op.add_column(sa.Column("uuid_id", sa.Uuid(), nullable=True))

    op.execute("UPDATE background_tasks SET uuid_id = lower(hex(randomblob(16)))")

    with op.batch_alter_table("background_tasks") as batch_op:
        batch_op.alter_column("uuid_id", nullable=False)
        batch_op.drop_column("id")
        batch_op.alter_column("uuid_id", new_column_name="id")
        batch_op.create_primary_key("pk_background_tasks", ["id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE background_tasks ADD COLUMN int_id INTEGER")
        op.execute(
            """
            WITH numbered AS (
                SELECT id, row_number() OVER (ORDER BY created_at, id)::integer AS new_id
                FROM background_tasks
            )
            UPDATE background_tasks
            SET int_id = numbered.new_id
            FROM numbered
            WHERE background_tasks.id = numbered.id
            """
        )
        op.execute("ALTER TABLE background_tasks ALTER COLUMN int_id SET NOT NULL")
        op.execute("ALTER TABLE background_tasks DROP CONSTRAINT background_tasks_pkey")
        op.execute("ALTER TABLE background_tasks DROP COLUMN id")
        op.execute("ALTER TABLE background_tasks RENAME COLUMN int_id TO id")
        op.execute("ALTER TABLE background_tasks ADD PRIMARY KEY (id)")
        return

    with op.batch_alter_table("background_tasks") as batch_op:
        batch_op.add_column(sa.Column("int_id", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE background_tasks
        SET int_id = (
            SELECT count(*)
            FROM background_tasks AS earlier
            WHERE earlier.created_at <= background_tasks.created_at
        )
        """
    )

    with op.batch_alter_table("background_tasks") as batch_op:
        batch_op.alter_column("int_id", nullable=False)
        batch_op.drop_column("id")
        batch_op.alter_column("int_id", new_column_name="id")
        batch_op.create_primary_key("pk_background_tasks", ["id"])

"""encrypt email bodies at rest

Revision ID: 20260614_0007
Revises: 20260601_0006
Create Date: 2026-06-14 00:00:00.000000
"""

from __future__ import annotations

import base64
import json
import os

import sqlalchemy as sa
from alembic import op
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


revision = "20260614_0007"
down_revision = "20260601_0006"
branch_labels = None
depends_on = None

NONCE_SIZE = 12


def _encrypt_text(plaintext: str) -> str:
    key_hex = os.environ.get("ENCRYPTION_KEY_HEX")
    if not key_hex:
        raise RuntimeError("ENCRYPTION_KEY_HEX is required to migrate email bodies")
    aesgcm = AESGCM(bytes.fromhex(key_hex))
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("emails")}
    if "body_encrypted" not in columns:
        op.add_column("emails", sa.Column("body_encrypted", sa.Text(), nullable=True))

    if "body" in columns:
        rows = bind.execute(sa.text("SELECT id, body FROM emails")).mappings()
        for row in rows:
            raw_body = row["body"]
            if isinstance(raw_body, str):
                serialized = raw_body
            else:
                serialized = json.dumps(
                    raw_body or {},
                    separators=(",", ":"),
                    sort_keys=True,
                )
            bind.execute(
                sa.text(
                    "UPDATE emails SET body_encrypted = :body_encrypted WHERE id = :id"
                ),
                {"id": row["id"], "body_encrypted": _encrypt_text(serialized)},
            )
    bind.execute(
        sa.text(
            "UPDATE emails SET body_encrypted = :body_encrypted "
            "WHERE body_encrypted IS NULL"
        ),
        {"body_encrypted": _encrypt_text("{}")},
    )

    with op.batch_alter_table("emails") as batch_op:
        batch_op.alter_column("body_encrypted", nullable=False)
        if "body" in columns:
            batch_op.drop_column("body")


def downgrade() -> None:
    with op.batch_alter_table("emails") as batch_op:
        batch_op.add_column(sa.Column("body", sa.JSON(), nullable=True))
        batch_op.drop_column("body_encrypted")

"""Email repository helpers."""

from datetime import datetime

import json

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role
from app.common.time import utc_now
from app.models.client import Client
from app.models.email import Email
from app.models.email_summary import EmailSummary


async def list_client_emails(
    session: AsyncSession, client_id: int, limit: int = 50
) -> list[Email]:
    """List recent client emails."""
    result = await session.execute(
        select(Email)
        .where(Email.client_id == client_id)
        .order_by(Email.sent_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_emails_for_summary(
    session: AsyncSession, client_id: int, start_date: datetime, end_date: datetime
) -> list[Email]:
    """Get emails for client within date range, ordered by sent_at."""
    result = await session.execute(
        select(Email)
        .where(Email.client_id == client_id)
        .where(Email.sent_at >= start_date)
        .where(Email.sent_at <= end_date)
        .order_by(Email.sent_at.asc())
    )
    return list(result.scalars().all())


async def count_emails_sent_after(
    session: AsyncSession, client_id: int, after: datetime
) -> int:
    """Count emails for client sent after given timestamp."""
    result = await session.execute(
        select(func.count())
        .select_from(Email)
        .where(Email.client_id == client_id)
        .where(Email.sent_at > after)
    )
    return int(result.scalar_one())


async def count_emails_captured_after(
    session: AsyncSession, client_id: int, after: datetime
) -> int:
    """Count emails captured by the system after a summary refresh timestamp."""
    result = await session.execute(
        select(func.count())
        .select_from(Email)
        .where(Email.client_id == client_id)
        .where(Email.captured_at > after)
    )
    return int(result.scalar_one())


async def list_accessible_email_summary_rows(
    session: AsyncSession,
    *,
    role: Role,
    firm_id: int,
    client_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[tuple[Email, Client, EmailSummary]]:
    """List accessible email rows with summary embeddings for service ranking."""
    statement = (
        select(Email, Client, EmailSummary)
        .join(Client, Email.client_id == Client.id)
        .join(EmailSummary, Email.client_id == EmailSummary.client_id)
        .where(EmailSummary.embedding.is_not(None))
    )

    if role != Role.superuser:
        statement = statement.where(Client.firm_id == firm_id)
    if client_id is not None:
        statement = statement.where(Email.client_id == client_id)
    if start_date is not None:
        statement = statement.where(Email.sent_at >= start_date)
    if end_date is not None:
        statement = statement.where(Email.sent_at <= end_date)

    result = await session.execute(statement)
    return list(result.all())


async def list_accessible_email_rows(
    session: AsyncSession,
    *,
    role: Role,
    firm_id: int,
    client_id: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    search_terms: list[str] | None = None,
    limit: int | None = None,
) -> list[tuple[Email, Client]]:
    """List accessible email rows for keyword search using DB-side filtering."""
    statement = select(Email, Client).join(Client, Email.client_id == Client.id)

    if role != Role.superuser:
        statement = statement.where(Client.firm_id == firm_id)
    if client_id is not None:
        statement = statement.where(Email.client_id == client_id)
    if start_date is not None:
        statement = statement.where(Email.sent_at >= start_date)
    if end_date is not None:
        statement = statement.where(Email.sent_at <= end_date)
    if search_terms:
        predicates = []
        for term in search_terms:
            pattern = f"%{term}%"
            predicates.extend(
                [
                    Email.subject.ilike(pattern),
                    Email.sender_address.ilike(pattern),
                    Client.name.ilike(pattern),
                    Client.external_email.ilike(pattern),
                ]
            )
        statement = statement.where(or_(*predicates))
    if limit is not None:
        statement = statement.order_by(Email.sent_at.desc()).limit(limit)

    result = await session.execute(statement)
    return list(result.all())


async def upsert_email_embedding(
    session: AsyncSession, *, email_id: int, embedding: list[float]
) -> None:
    """Persist an email embedding for pgvector retrieval fallback."""
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        vector = "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"
        await session.execute(
            text(
                """
                INSERT INTO email_embeddings (email_id, embedding, created_at)
                VALUES (:email_id, CAST(:embedding AS vector), :created_at)
                ON CONFLICT (email_id)
                DO UPDATE SET embedding = EXCLUDED.embedding, created_at = EXCLUDED.created_at
                """
            ),
            {"email_id": email_id, "embedding": vector, "created_at": utc_now()},
        )
        return

    await session.execute(
        text(
            """
            INSERT INTO email_embeddings (email_id, embedding, created_at)
            VALUES (:email_id, :embedding, :created_at)
            ON CONFLICT(email_id)
            DO UPDATE SET embedding = excluded.embedding, created_at = excluded.created_at
        """
        ),
        {
            "email_id": email_id,
            "embedding": json.dumps(embedding, separators=(",", ":")),
            "created_at": utc_now(),
        },
    )

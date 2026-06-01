"""Production vector search providers for email context.

Azure AI Search is the primary retriever when configured. pgvector is the
fallback for self-hosted/open-source deployments. Callers should still keep a
plain database keyword fallback so local SQLite development remains lightweight.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role
from app.core.logging_config import get_logger
from app.core.setting import settings
from app.llm.embeddings import embed_text_async

logger = get_logger("vectorizer.retrievers")


@dataclass(frozen=True)
class RetrievalDocument:
    """Provider-neutral email context document."""

    id: int
    client_id: int
    client_name: str
    sender_email: str
    recipients: list[str]
    subject: str
    content: str
    sent_at: datetime
    relevance_score: float
    provider: str


def _azure_configured() -> bool:
    return bool(
        settings.azure_ai_search_endpoint
        and settings.azure_ai_search_api_key
        and settings.azure_ai_search_index_name
    )


def _odata_filter(
    *,
    role: Role,
    firm_id: int | None,
    client_id: int | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> str | None:
    clauses: list[str] = []
    if role != Role.superuser and firm_id is not None:
        clauses.append(f"firmId eq {firm_id}")
    if client_id is not None:
        clauses.append(f"clientId eq {client_id}")
    if start_date is not None:
        clauses.append(f"sentAt ge {start_date.isoformat()}")
    if end_date is not None:
        clauses.append(f"sentAt le {end_date.isoformat()}")
    return " and ".join(clauses) if clauses else None


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("retrieval document is missing sentAt")


def _coerce_recipients(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if isinstance(value, str) and value:
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _azure_document(raw: dict[str, Any]) -> RetrievalDocument:
    return RetrievalDocument(
        id=int(raw.get("emailId") or raw.get("id")),
        client_id=int(raw["clientId"]),
        client_name=str(raw.get("clientName") or ""),
        sender_email=str(raw.get("senderEmail") or raw.get("sender_address") or ""),
        recipients=_coerce_recipients(raw.get("recipients")),
        subject=str(raw.get("subject") or ""),
        content=str(raw.get("content") or raw.get("body") or ""),
        sent_at=_coerce_datetime(raw.get("sentAt") or raw.get("sent_at")),
        relevance_score=float(
            raw.get("@search.rerankerScore") or raw.get("@search.score") or 0.0
        ),
        provider="azure_ai_search",
    )


async def _retrieve_from_azure(
    *,
    query: str,
    role: Role,
    firm_id: int | None,
    client_id: int | None,
    start_date: datetime | None,
    end_date: datetime | None,
    limit: int,
) -> list[RetrievalDocument]:
    if not _azure_configured():
        return []

    endpoint = settings.azure_ai_search_endpoint.rstrip("/")
    url = (
        f"{endpoint}/indexes/{settings.azure_ai_search_index_name}/docs/search"
        f"?api-version={settings.azure_ai_search_api_version}"
    )
    embedding = await embed_text_async(query)
    payload: dict[str, Any] = {
        "search": query,
        "top": limit,
        "select": "emailId,clientId,firmId,clientName,senderEmail,recipients,subject,content,sentAt",
        "vectorQueries": [
            {
                "kind": "vector",
                "vector": embedding,
                "fields": settings.azure_ai_search_content_vector_field,
                "k": limit,
            }
        ],
    }
    filters = _odata_filter(
        role=role,
        firm_id=firm_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
    )
    if filters:
        payload["filter"] = filters
    if settings.azure_ai_search_semantic_configuration:
        payload.update(
            {
                "queryType": "semantic",
                "semanticConfiguration": settings.azure_ai_search_semantic_configuration,
            }
        )

    headers = {
        "api-key": settings.azure_ai_search_api_key,
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("azure_ai_search_unavailable error=%s", exc)
        return []

    documents = []
    for item in data.get("value", []):
        try:
            documents.append(_azure_document(item))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("azure_ai_search_bad_document error=%s", exc)
    return documents


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


async def _retrieve_from_pgvector(
    session: AsyncSession,
    *,
    query: str,
    role: Role,
    firm_id: int | None,
    client_id: int | None,
    start_date: datetime | None,
    end_date: datetime | None,
    limit: int,
) -> list[RetrievalDocument]:
    if not settings.pgvector_enabled:
        return []
    if session is None:
        return []

    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return []

    where_clauses = ["1 = 1"]
    params: dict[str, Any] = {
        "limit": limit,
        "query_vector": _vector_literal(await embed_text_async(query)),
    }
    if role != Role.superuser and firm_id is not None:
        where_clauses.append("c.firm_id = :firm_id")
        params["firm_id"] = firm_id
    if client_id is not None:
        where_clauses.append("e.client_id = :client_id")
        params["client_id"] = client_id
    if start_date is not None:
        where_clauses.append("e.sent_at >= :start_date")
        params["start_date"] = start_date
    if end_date is not None:
        where_clauses.append("e.sent_at <= :end_date")
        params["end_date"] = end_date

    statement = text(
        f"""
        SELECT
            e.id,
            e.client_id,
            c.name AS client_name,
            e.sender_address,
            e.to_recipients,
            e.subject,
            e.body,
            e.sent_at,
            1 - (ee.embedding <=> CAST(:query_vector AS vector)) AS relevance_score
        FROM email_embeddings ee
        JOIN emails e ON e.id = ee.email_id
        JOIN clients c ON c.id = e.client_id
        WHERE {" AND ".join(where_clauses)}
        ORDER BY ee.embedding <=> CAST(:query_vector AS vector)
        LIMIT :limit
        """
    )
    try:
        result = await session.execute(statement, params)
    except Exception as exc:
        logger.warning("pgvector_retrieval_unavailable error=%s", exc)
        return []

    documents = []
    for row in result.mappings():
        body = row["body"]
        content = body.get("content", "") if isinstance(body, dict) else str(body or "")
        documents.append(
            RetrievalDocument(
                id=int(row["id"]),
                client_id=int(row["client_id"]),
                client_name=str(row["client_name"] or ""),
                sender_email=str(row["sender_address"] or ""),
                recipients=_coerce_recipients(row["to_recipients"]),
                subject=str(row["subject"] or ""),
                content=content,
                sent_at=row["sent_at"],
                relevance_score=float(row["relevance_score"] or 0.0),
                provider="pgvector",
            )
        )
    return documents


async def retrieve_email_context(
    session: AsyncSession,
    *,
    query: str,
    role: Role,
    firm_id: int | None,
    client_id: int | None,
    start_date: datetime | None,
    end_date: datetime | None,
    limit: int,
) -> list[RetrievalDocument]:
    """Retrieve email context via Azure AI Search with pgvector fallback."""
    if not settings.vectorizer_enabled:
        return []

    azure_documents = await _retrieve_from_azure(
        query=query,
        role=role,
        firm_id=firm_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    if azure_documents:
        return azure_documents

    return await _retrieve_from_pgvector(
        session,
        query=query,
        role=role,
        firm_id=firm_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )

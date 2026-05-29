"""Search ranking helpers."""
import math

from app.models.clients import Client
from app.models.summaries import Email, EmailSummary


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b):
        return 0.0
    dot_product = sum(a_value * b_value for a_value, b_value in zip(a, b))
    norm_a = math.sqrt(sum(value * value for value in a))
    norm_b = math.sqrt(sum(value * value for value in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def rank_email_summary_rows(
    rows: list[tuple[Email, Client, EmailSummary]],
    *,
    query_embedding: list[float],
    limit: int,
) -> list[tuple[Email, Client]]:
    """Rank email rows by their client summary embedding."""
    scored_results = []
    for email, client, summary in rows:
        if summary.embedding:
            similarity = cosine_similarity(query_embedding, summary.embedding)
            scored_results.append((similarity, email, client))

    scored_results.sort(key=lambda item: item[0], reverse=True)
    return [(email, client) for _, email, client in scored_results[:limit]]

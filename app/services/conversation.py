"""Conversation services over email context."""

import re
from datetime import datetime, time, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Role
from app.models.users import User
from app.repositories.clients import list_client_inference_candidates
from app.schemas.conversation import ConversationResponse
from app.services.email_search import search_email_context

_STOPWORDS = {
    "a",
    "about",
    "all",
    "an",
    "and",
    "any",
    "are",
    "as",
    "ask",
    "can",
    "context",
    "conversation",
    "day",
    "days",
    "did",
    "do",
    "does",
    "email",
    "emails",
    "find",
    "for",
    "from",
    "give",
    "i",
    "in",
    "is",
    "latest",
    "last",
    "me",
    "message",
    "messages",
    "month",
    "months",
    "of",
    "on",
    "please",
    "recent",
    "show",
    "summarize",
    "summary",
    "tell",
    "the",
    "to",
    "today",
    "was",
    "week",
    "weeks",
    "were",
    "what",
    "when",
    "where",
    "who",
    "why",
    "with",
    "yesterday",
    "you",
}


def _day_bounds(value: datetime) -> tuple[datetime, datetime]:
    day = value.date()
    return datetime.combine(day, time.min), datetime.combine(day, time.max)


def _extract_iso_dates(question: str) -> list[datetime]:
    dates = []
    for match in re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", question):
        try:
            dates.append(datetime.strptime(match, "%Y-%m-%d"))
        except ValueError:
            continue
    return dates


def _extract_conversation_date_range(
    question: str,
) -> tuple[Optional[datetime], Optional[datetime]]:
    lowered = question.lower()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    relative = re.search(
        r"\blast\s+(\d{1,3})\s+(day|days|week|weeks|month|months)\b",
        lowered,
    )
    if relative:
        amount = int(relative.group(1))
        unit = relative.group(2)
        days = amount
        if unit.startswith("week"):
            days = amount * 7
        elif unit.startswith("month"):
            days = amount * 30
        return now - timedelta(days=days), now

    if "yesterday" in lowered:
        return _day_bounds(now - timedelta(days=1))
    if "today" in lowered:
        return _day_bounds(now)

    dates = _extract_iso_dates(question)
    if len(dates) >= 2:
        start = datetime.combine(dates[0].date(), time.min)
        end = datetime.combine(dates[1].date(), time.max)
        return min(start, end), max(start, end)
    if len(dates) == 1:
        return _day_bounds(dates[0])

    return None, None


def _extract_conversation_limit(question: str) -> int:
    lowered = question.lower()
    match = re.search(
        r"\b(?:last|latest|top|first|recent)\s+(\d{1,2})\s+(?:emails?|messages?)\b",
        lowered,
    )
    if not match:
        return 10
    return max(1, min(int(match.group(1)), 50))


def _conversation_search_query(question: str) -> str:
    """Extract useful search keywords from a natural-language question."""
    tokens = [
        token.strip(".,?!:;()[]{}\"'")
        for token in re.findall(r"[a-zA-Z0-9@._+-]+", question.lower())
    ]
    meaningful = [
        token
        for token in tokens
        if len(token) >= 2 and not token.isdigit() and token not in _STOPWORDS
    ]
    return " ".join(meaningful) if meaningful else question.strip()


async def _infer_conversation_client_id(
    session: AsyncSession,
    *,
    current_user: User,
    question: str,
) -> Optional[int]:
    lowered = question.lower()
    role = Role(current_user.role.value)
    emails = sorted(
        set(re.findall(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b", lowered))
    )
    client_ids = [
        int(match) for match in re.findall(r"\bclient\s+#?(\d{1,10})\b", lowered)
    ]
    name_terms = [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z'-]{2,}", lowered)
        if token not in _STOPWORDS
    ][:12]
    clients = await list_client_inference_candidates(
        session,
        role=role,
        firm_id=current_user.firm_id,
        emails=emails,
        client_ids=client_ids,
        name_terms=name_terms,
    )
    scored: list[tuple[int, int, int]] = []

    for client in clients:
        score = 0
        name = client.name.lower()
        email = client.external_email.lower()
        if email and email in lowered:
            score = max(score, 100)
        if name and name in lowered:
            score = max(score, 90 + len(name))
        if re.search(rf"\bclient\s+#?{client.id}\b", lowered):
            score = max(score, 80)

        name_parts = [part for part in re.split(r"\s+", name) if len(part) >= 3]
        matched_parts = sum(
            1 for part in name_parts if re.search(rf"\b{re.escape(part)}\b", lowered)
        )
        if matched_parts and matched_parts == len(name_parts):
            score = max(score, 70 + matched_parts)
        elif matched_parts:
            score = max(score, 40 + matched_parts)

        if score:
            scored.append((score, len(name), client.id))

    if not scored:
        return None

    scored.sort(reverse=True)
    if (
        len(scored) > 1
        and scored[0][0] == scored[1][0]
        and scored[0][1] == scored[1][1]
    ):
        return None
    return scored[0][2]


async def answer_email_context_question(
    session: AsyncSession,
    *,
    current_user: User,
    question: str,
) -> ConversationResponse:
    """Answer a natural-language question from accessible email context."""
    client_id = await _infer_conversation_client_id(
        session,
        current_user=current_user,
        question=question,
    )
    start_date, end_date = _extract_conversation_date_range(question)
    limit = _extract_conversation_limit(question)
    search_query = _conversation_search_query(question)

    search_response = await search_email_context(
        session,
        current_user=current_user,
        query=search_query,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    if not search_response.results and (
        client_id is not None or start_date or end_date
    ):
        search_response = await search_email_context(
            session,
            current_user=current_user,
            query=search_query,
            limit=limit,
        )

    if not search_response.results:
        return ConversationResponse(
            question=question,
            answer="No matching emails were found in the accessible context.",
            source_email_count=0,
            sources=[],
        )

    open_items = []
    concluded = []
    for source in search_response.results[:5]:
        text = f"{source.subject}: {source.snippet}"
        if any(
            word in text.lower()
            for word in ["need", "missing", "send", "action", "todo", "please"]
        ):
            open_items.append(text)
        else:
            concluded.append(text)

    answer_parts = [
        f"Found {len(search_response.results)} relevant email(s).",
        f"Most relevant: {search_response.results[0].subject}.",
    ]
    if open_items:
        answer_parts.append("Likely open items: " + " | ".join(open_items[:3]))
    if concluded:
        answer_parts.append("Related context: " + " | ".join(concluded[:2]))

    return ConversationResponse(
        question=question,
        answer=" ".join(answer_parts),
        source_email_count=len(search_response.results),
        sources=search_response.results,
    )

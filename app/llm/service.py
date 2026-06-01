import asyncio
import json
import random
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core import settings
from app.core.logging_config import get_logger
from app.llm.prompts import render_prompt

try:
    from prometheus_client import Counter
except (
    ModuleNotFoundError
):  # pragma: no cover - dependency is declared for runtime images
    Counter = None


if Counter is not None:
    LLM_REQUESTS = Counter(
        "llm_requests_total",
        "LLM summarization requests by model and outcome.",
        ["model", "outcome"],
    )
    LLM_TOKENS = Counter(
        "llm_tokens_total",
        "LLM summarization token usage by model and direction.",
        ["model", "direction"],
    )
else:
    LLM_REQUESTS = None
    LLM_TOKENS = None

logger = get_logger("llm.service")
MAX_EMAILS_PER_SUMMARY = 80
MAX_EMAIL_BODY_CHARS = 4_000


class LLMEmailSummary(BaseModel):
    """Validated structured LLM summary payload."""

    summary_text: str = Field(default="", max_length=10_000)
    actors: list[str] = Field(default_factory=list, max_length=50)
    concluded_discussions: list[str] = Field(default_factory=list, max_length=100)
    open_action_items: list[str] = Field(default_factory=list, max_length=100)

    model_config = ConfigDict(extra="ignore")

    def to_result(self) -> dict[str, Any]:
        return self.model_dump()


class LLMService:
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def summarize(
        self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        bounded_emails = self._bounded_emails(emails)
        prompt = self._build_prompt(bounded_emails, start_date, end_date)
        if not self.api_key:
            result = self._mock_response(bounded_emails, start_date, end_date)
            self._record_metrics("mock", result)
            return result
        try:
            result = await self._call_provider(prompt)
        except Exception:
            self._record_metrics("error")
            raise
        self._record_metrics("success", result)
        return result

    def _build_prompt(
        self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime
    ) -> str:
        return render_prompt(
            "summarization",
            emails=self._format_emails(emails),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

    def _bounded_emails(self, emails: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sorted_emails = sorted(emails, key=lambda item: item["sent_at"], reverse=True)
        bounded = sorted_emails[:MAX_EMAILS_PER_SUMMARY]
        if len(emails) > len(bounded):
            logger.info(
                "llm_email_input_truncated original_count=%s kept_count=%s",
                len(emails),
                len(bounded),
            )
        return bounded

    def _format_emails(self, emails: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for email in emails:
            lines.append(
                f"<email sent_at={email['sent_at'].isoformat()} sender={email['sender_email']!r}>"
            )
            lines.append(f"<recipients>{', '.join(email['recipients'])}</recipients>")
            lines.append(f"<subject>{email['subject']}</subject>")
            lines.append(f"<body>{str(email['body'])[:MAX_EMAIL_BODY_CHARS]}</body>")
            lines.append("</email>")
        return "\n".join(lines).strip()

    def _record_metrics(
        self, outcome: str, result: dict[str, Any] | None = None
    ) -> None:
        if LLM_REQUESTS is None or LLM_TOKENS is None:
            return
        LLM_REQUESTS.labels(model=self.model, outcome=outcome).inc()
        if not result:
            return
        LLM_TOKENS.labels(model=self.model, direction="input").inc(
            int(result.get("token_in") or 0)
        )
        LLM_TOKENS.labels(model=self.model, direction="output").inc(
            int(result.get("token_out") or 0)
        )

    async def _call_provider(self, prompt: str) -> dict[str, Any]:
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 600,
                "temperature": 0.2,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "object",
                    "properties": {
                        "summary_text": {"type": "string"},
                        "actors": {"type": "array", "items": {"type": "string"}},
                        "concluded_discussions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "open_action_items": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "summary_text",
                        "actors",
                        "concluded_discussions",
                        "open_action_items",
                    ],
                },
            },
        }
        delays = [1.0, 2.0, 4.0]
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt, delay in enumerate(delays + [None]):
                try:
                    response = await client.post(
                        self.endpoint, headers=headers, json=payload
                    )
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_response(data)
                except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
                    last_error = exc
                    if attempt == len(delays):
                        break
                    retry_after = None
                    if isinstance(exc, httpx.HTTPStatusError):
                        retry_after = exc.response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            delay = max(delay, float(retry_after))
                        except ValueError:
                            pass
                    await asyncio.sleep(delay + random.random() * 0.2)
        raise RuntimeError("LLM summarization failed after retries") from last_error

    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any]:
        text = None
        if "candidates" in data and data["candidates"]:
            candidate = data["candidates"][0]
            content = candidate.get("content")
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list) and parts:
                    text = (
                        parts[0].get("text") if isinstance(parts[0], dict) else parts[0]
                    )
            elif isinstance(content, list) and content:
                text = (
                    content[0].get("text")
                    if isinstance(content[0], dict)
                    else content[0]
                )
            elif isinstance(content, str):
                text = content
        if text is None:
            text = (
                data.get("output", {}).get("text")
                if isinstance(data.get("output"), dict)
                else None
            )
        if text is None:
            text = json.dumps(data)
        result = self._parse_json_text(text)
        tokens = data.get("usageMetadata") or data.get("usage", {})
        result["token_in"] = (
            tokens.get("promptTokenCount")
            or tokens.get("prompt_tokens")
            or tokens.get("input_tokens")
            or max(1, len(text) // 4)
        )
        result["token_out"] = (
            tokens.get("candidatesTokenCount")
            or tokens.get("completion_tokens")
            or tokens.get("output_tokens")
            or max(1, len(result.get("summary_text", "")) // 4)
        )
        return result

    def _parse_json_text(self, raw: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return LLMEmailSummary.model_validate(parsed).to_result()
        except (json.JSONDecodeError, ValidationError):
            pass
        return LLMEmailSummary(summary_text=raw.strip()).to_result()

    def _mock_response(
        self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        actors = {email["sender_email"] for email in emails}
        summary_text = "\n".join(
            [f"{email['sender_email']}: {email['subject']}" for email in emails]
        )
        return {
            "summary_text": f"Mock summary for {len(emails)} emails from {start_date.date()} to {end_date.date()}.\n"
            + summary_text,
            "actors": sorted(list(actors))[:5],
            "concluded_discussions": [
                "Gathered missing client documents",
                "Confirmed next follow-up by accountant",
            ],
            "open_action_items": ["Client to send W-2", "Schedule signature review"],
            "token_in": max(1, len(summary_text) // 4),
            "token_out": max(1, 50),
        }

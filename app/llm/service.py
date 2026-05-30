import asyncio
import json
import random
from datetime import datetime
from typing import Any

import httpx

from app.core import settings
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


class LLMService:
    def __init__(self) -> None:
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def summarize(
        self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        prompt = self._build_prompt(emails, start_date, end_date)
        if not self.api_key:
            result = self._mock_response(emails, start_date, end_date)
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

    def _format_emails(self, emails: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for email in emails:
            lines.append(
                f"[{email['sent_at'].isoformat()}] {email['sender_email']} -> {', '.join(email['recipients'])}"
            )
            lines.append(f"Subject: {email['subject']}")
            lines.append(email["body"])
            lines.append("\n")
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
                return {
                    "summary_text": parsed.get("summary_text", ""),
                    "actors": parsed.get("actors", []),
                    "concluded_discussions": parsed.get("concluded_discussions", []),
                    "open_action_items": parsed.get("open_action_items", []),
                }
        except json.JSONDecodeError:
            pass
        return {
            "summary_text": raw.strip(),
            "actors": [],
            "concluded_discussions": [],
            "open_action_items": [],
        }

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

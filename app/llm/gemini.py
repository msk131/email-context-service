import asyncio
import json
import random
from datetime import datetime
from typing import Any

import httpx

from app.core import settings


class GeminiService:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.endpoint = f"https://gemini.googleapis.com/v1/models/{self.model}:generateText"

    async def summarize(
        self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime
    ) -> dict[str, Any]:
        prompt = self._build_prompt(emails, start_date, end_date)
        if not self.api_key:
            return self._mock_response(emails, start_date, end_date)
        return await self._call_gemini(prompt)

    def _build_prompt(
        self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime
    ) -> str:
        lines = [
            "You are an email summarization assistant for CPA teams."
            "Extract the following from the email thread between accountants and a client:",
            "1. Actors mentioned (names / roles).",
            "2. Concluded discussions.",
            "3. Open action items.",
            "Return valid JSON with keys: actors, concluded_discussions, open_action_items, summary_text.",
            f"Date range: {start_date.isoformat()} to {end_date.isoformat()}.",
            "If a field is empty, return an empty array for that field.",
            "Email thread:\n",
        ]
        for email in emails:
            lines.append(
                f"[{email['sent_at'].isoformat()}] {email['sender_email']} -> {', '.join(email['recipients'])}"
            )
            lines.append(f"Subject: {email['subject']}")
            lines.append(email["body"])
            lines.append("\n")
        return "\n".join(lines)

    async def _call_gemini(self, prompt: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"prompt": {"text": prompt}, "max_output_tokens": 600, "temperature": 0.2}
        delays = [1.0, 2.0, 4.0]
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt, delay in enumerate(delays + [None]):
                try:
                    response = await client.post(self.endpoint, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return self._parse_response(data)
                except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
                    last_error = exc
                    if attempt == len(delays):
                        break
                    await asyncio.sleep(delay + random.random() * 0.2)
        raise RuntimeError("Gemini summarization failed after retries") from last_error

    def _parse_response(self, data: dict[str, Any]) -> dict[str, Any]:
        text = None
        if "candidates" in data and data["candidates"]:
            candidate = data["candidates"][0]
            content = candidate.get("content")
            if isinstance(content, list) and content:
                text = content[0].get("text") if isinstance(content[0], dict) else content[0]
            elif isinstance(content, str):
                text = content
        if text is None:
            text = data.get("output", {}).get("text") if isinstance(data.get("output"), dict) else None
        if text is None:
            text = json.dumps(data)
        result = self._parse_json_text(text)
        tokens = data.get("usage", {})
        result["token_in"] = (
            tokens.get("prompt_tokens")
            or tokens.get("input_tokens")
            or max(1, len(text) // 4)
        )
        result["token_out"] = (
            tokens.get("completion_tokens")
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
        summary_text = "\n".join([f"{email['sender_email']}: {email['subject']}" for email in emails])
        return {
            "summary_text": f"Mock summary for {len(emails)} emails from {start_date.date()} to {end_date.date()}.\n"
            + summary_text,
            "actors": sorted(list(actors))[:5],
            "concluded_discussions": ["Gathered missing client documents", "Confirmed next follow-up by accountant"],
            "open_action_items": ["Client to send W-2", "Schedule signature review"],
            "token_in": max(1, len(summary_text) // 4),
            "token_out": max(1, 50),
        }

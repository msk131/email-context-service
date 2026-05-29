import json
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.llm.llm_client import LLMClient
from app.llm.prompts import render_prompt

class GeminiService:
    def __init__(self) -> None:
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.endpoint = f"https://gemini.googleapis.com/v1/models/{self.model}:generateText"
        self.client = LLMClient(api_key=self.api_key, model=self.model, endpoint=self.endpoint, timeout=30.0)

    async def summarize(self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime) -> dict[str, Any]:
        prompt = self._build_prompt(emails, start_date, end_date)
        if not self.api_key:
            return self._mock_response(emails, start_date, end_date)
        return await self._call_gemini(prompt)

    def _build_prompt(self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime) -> str:
        # Render using prompt templates (RAG prompt configuration)
        email_lines = []
        for email in emails:
            sent = email.get("sent_at")
            sent_s = sent.isoformat() if hasattr(sent, "isoformat") else str(sent)
            recipients = ", ".join(email.get("recipients") or [])
            email_lines.append(f"[{sent_s}] {email.get('sender_email')} -> {recipients}\nSubject: {email.get('subject')}\n{email.get('body')}\n")
        emails_text = "\n".join(email_lines)
        return render_prompt(
            "summarization",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            emails=emails_text,
        )

    async def _call_gemini(self, prompt: str) -> dict[str, Any]:
        payload = {"prompt": {"text": prompt}, "max_output_tokens": 600, "temperature": 0.2}
        data = await self.client.generate(payload)
        return self._parse_response(data)

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
        result["token_in"] = tokens.get("prompt_tokens") or tokens.get("input_tokens") or max(1, len(text) // 4)
        result["token_out"] = tokens.get("completion_tokens") or tokens.get("output_tokens") or max(1, len(result.get("summary_text", "")) // 4)
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

    def _mock_response(self, emails: list[dict[str, Any]], start_date: datetime, end_date: datetime) -> dict[str, Any]:
        actors = {email["sender_email"] for email in emails}
        summary_text = "\n".join([f"{email['sender_email']}: {email['subject']}" for email in emails])
        return {
            "summary_text": f"Mock summary for {len(emails)} emails from {start_date.date()} to {end_date.date()}.\n" + summary_text,
            "actors": sorted(list(actors))[:5],
            "concluded_discussions": ["Gathered missing client documents", "Confirmed next follow-up by accountant"],
            "open_action_items": ["Client to send W-2", "Schedule signature review"],
            "token_in": max(1, len(summary_text) // 4),
            "token_out": max(1, 50),
        }

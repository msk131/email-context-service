from datetime import datetime

import pytest

from app.llm.gemini import GeminiService as GeminiGeminiService
from app.llm.llm import GeminiService as GeminiLLMService


@pytest.mark.asyncio
async def test_llm_summarize_returns_mock_response_when_api_key_missing():
    service = GeminiLLMService()
    service.api_key = ""
    emails = [
        {
            "sent_at": datetime(2025, 1, 1, 12, 0),
            "sender_email": "acct@example.com",
            "recipients": ["client@example.com"],
            "subject": "Payroll update",
            "body": "Please send payroll documents.",
        }
    ]

    result = await service.summarize(emails, datetime(2025, 1, 1), datetime(2025, 1, 2))

    assert result["summary_text"].startswith("Mock summary for 1 emails")
    assert "Payroll update" in result["summary_text"]
    assert result["actors"] == ["acct@example.com"]
    assert result["token_in"] >= 1
    assert result["token_out"] >= 50


def test_llm_parse_response_candidates_and_tokens():
    service = GeminiGeminiService()
    data = {
        "candidates": [
            {
                "content": [
                    {"text": '{"summary_text": "OK", "actors": ["acct@example.com"]}'}
                ]
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 7},
    }

    result = service._parse_response(data)

    assert result["summary_text"] == "OK"
    assert result["actors"] == ["acct@example.com"]
    assert result["token_in"] == 3
    assert result["token_out"] == 7


def test_llm_parse_json_text_falls_back_for_non_json():
    service = GeminiGeminiService()
    raw = "Not valid JSON"

    parsed = service._parse_json_text(raw)

    assert parsed["summary_text"] == raw
    assert parsed["actors"] == []
    assert parsed["concluded_discussions"] == []
    assert parsed["open_action_items"] == []

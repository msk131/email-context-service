from datetime import datetime

import pytest

from app.llm.service import LLMService


@pytest.mark.asyncio
async def test_llm_summarize_returns_mock_response_when_api_key_missing():
    service = LLMService()
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
    service = LLMService()
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"summary_text": "OK", "actors": ["acct@example.com"]}'
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 3, "candidatesTokenCount": 7},
    }

    result = service._parse_response(data)

    assert result["summary_text"] == "OK"
    assert result["actors"] == ["acct@example.com"]
    assert result["token_in"] == 3
    assert result["token_out"] == 7


def test_llm_uses_current_provider_generate_content_endpoint():
    service = LLMService()

    assert service.endpoint == (
        f"https://generativelanguage.googleapis.com/v1beta/models/{service.model}:generateContent"
    )


def test_llm_build_prompt_uses_yaml_template():
    service = LLMService()
    emails = [
        {
            "sent_at": datetime(2025, 1, 1, 12, 0),
            "sender_email": "acct@example.com",
            "recipients": ["client@example.com"],
            "subject": "Payroll update",
            "body": "Please send payroll documents.",
        }
    ]

    prompt = service._build_prompt(emails, datetime(2025, 1, 1), datetime(2025, 1, 2))

    assert "You are an email summarization assistant for CPA teams." in prompt
    assert "Date range: 2025-01-01T00:00:00 to 2025-01-02T00:00:00." in prompt
    assert "Payroll update" in prompt


def test_llm_parse_json_text_falls_back_for_non_json():
    service = LLMService()
    raw = "Not valid JSON"

    parsed = service._parse_json_text(raw)

    assert parsed["summary_text"] == raw
    assert parsed["actors"] == []
    assert parsed["concluded_discussions"] == []
    assert parsed["open_action_items"] == []

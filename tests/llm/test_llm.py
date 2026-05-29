from app.llm import LLMService
from datetime import datetime


def test_llm_service_parse_json_text():
    service = LLMService()
    response = service._parse_json_text(
        '{"summary_text": "Completed review.", "actors": ["John"], "concluded_discussions": ["Reviewed forms"], "open_action_items": ["Submit receipts"]}'
    )
    assert response["summary_text"] == "Completed review."
    assert response["actors"] == ["John"]
    assert response["concluded_discussions"] == ["Reviewed forms"]
    assert response["open_action_items"] == ["Submit receipts"]


def test_llm_service_mock_response_contains_keys():
    service = LLMService()
    now = datetime.now()
    emails = [
        {"sender_email": "john@example.org", "recipients": ["client@example.com"], "subject": "Test", "body": "Hello", "sent_at": now}
    ]
    output = service._mock_response(emails, now, now)
    assert "summary_text" in output
    assert "actors" in output
    assert "concluded_discussions" in output
    assert "open_action_items" in output

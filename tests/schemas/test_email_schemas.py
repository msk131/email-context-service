import pytest
from pydantic import ValidationError

from app.common.models import EmailDirection
from app.schemas.emails import MockEmailSendRequest, MockThreadRequest


def test_mock_email_request_requires_client_reference():
    with pytest.raises(ValidationError) as exc:
        MockEmailSendRequest(
            direction=EmailDirection.inbound,
            subject="Missing 1099-INT",
            body="Please send the missing form.",
        )

    assert "Provide client_id or both client_name and client_email" in str(exc.value)


def test_mock_thread_request_accepts_client_details():
    request = MockThreadRequest(
        client_name="Akshar Patel",
        client_email="akshar@example.org",
        message_count=6,
    )

    assert request.client_id is None
    assert request.client_email == "akshar@example.org"

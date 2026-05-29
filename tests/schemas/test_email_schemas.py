import pytest
from pydantic import ValidationError

from app.schemas.emails import (
    MockEmailReceiveRequest,
    MockEmailSendRequest,
)


def test_mock_send_email_request_accepts_graph_send_mail_payload():
    """Mock send accepts a Graph sendMail body with only capture-required fields."""
    request = MockEmailSendRequest(
        message={
            "body": {
                "contentType": "HTML",
                "content": "Please send the missing form.",
            },
            "sentDateTime": "2026-05-29T08:12:00Z",
            "from": {
                "emailAddress": {
                    "address": "accountant@example.org",
                    "name": "John",
                }
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": "akshar@example.org",
                        "name": "Akshar",
                    }
                }
            ],
            "ccRecipients": [
                {"emailAddress": {"address": "reviewer@example.org"}}
            ],
        },
        saveToSentItems=False,
    )

    assert request.message.subject is None
    assert request.message.body.content == "Please send the missing form."
    assert request.message.from_.emailAddress.address == "accountant@example.org"
    assert request.message.toRecipients[0].emailAddress.address == "akshar@example.org"
    assert request.saveToSentItems is False


def test_mock_receive_email_request_accepts_graph_message_payload():
    """Mock receive accepts a Graph message body with only capture-required fields."""
    request = MockEmailReceiveRequest(
        receivedDateTime="2026-05-29T08:12:00Z",
        body={"contentType": "Text", "content": "Attached now."},
        **{
            "from": {
                "emailAddress": {
                    "address": "akshar@example.org",
                    "name": "Akshar Patel",
                }
            }
        },
        toRecipients=[
            {
                "emailAddress": {
                    "address": "accountant@example.org",
                    "name": "John Accountant",
                }
            }
        ],
    )

    assert request.receivedDateTime is not None
    assert request.subject is None
    assert request.from_.emailAddress.address == "akshar@example.org"
    assert request.sender == request.from_


def test_mock_send_email_request_rejects_sender_in_recipients():
    """Test that sender cannot appear in recipients."""
    with pytest.raises(ValidationError) as exc:
        MockEmailSendRequest(
            message={
                "subject": "Self-sent email",
                "sentDateTime": "2026-05-29T08:12:00Z",
                "body": {"contentType": "HTML", "content": "This should fail."},
                "from": {"emailAddress": {"address": "same@example.org"}},
                "toRecipients": [
                    {"emailAddress": {"address": "same@example.org"}}
                ],
            }
        )

    assert "Sender cannot appear in recipients" in str(exc.value)


def test_mock_receive_email_request_requires_capture_fields():
    """Graph fields are optional, but capture needs sender, recipient, timestamp, and body."""
    with pytest.raises(ValidationError) as exc:
        MockEmailReceiveRequest(
            body={"contentType": "Text", "content": "Missing metadata."},
            **{"from": {"emailAddress": {"address": "akshar@example.org"}}},
        )

    assert "At least one recipient is required" in str(exc.value)

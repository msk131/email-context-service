"""Microsoft Graph-compatible email mock schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class GraphEmailAddress(BaseModel):
    """Microsoft Graph emailAddress resource."""

    address: EmailStr = Field(..., examples=["akshar@example.org"])
    name: str | None = Field(None, max_length=255, examples=["Akshar Patel"])

    model_config = ConfigDict(extra="allow")


class GraphRecipient(BaseModel):
    """Microsoft Graph recipient resource."""

    emailAddress: GraphEmailAddress

    model_config = ConfigDict(extra="allow")


class GraphItemBody(BaseModel):
    """Microsoft Graph itemBody resource."""

    contentType: str = Field("HTML", examples=["HTML", "Text"])
    content: str = Field(..., min_length=1, max_length=100_000)

    model_config = ConfigDict(extra="allow")


class GraphMessage(BaseModel):
    """
    Microsoft Graph message resource shape used by the mock API.

    Graph fields are accepted as optional, but this service requires the fields
    needed to capture an individual email: sender/from, recipients, timestamp,
    and body content.
    """

    odata_type: str | None = Field(None, alias="@odata.type")
    id: str | None = Field(None, max_length=255)
    createdDateTime: datetime | None = None
    lastModifiedDateTime: datetime | None = None
    receivedDateTime: datetime | None = None
    sentDateTime: datetime | None = None
    hasAttachments: bool | None = None
    internetMessageId: str | None = Field(None, max_length=998)
    subject: str | None = Field(None, max_length=512)
    bodyPreview: str | None = Field(None, max_length=1024)
    importance: str | None = Field(None, max_length=32)
    parentFolderId: str | None = Field(None, max_length=255)
    conversationId: str | None = Field(None, max_length=255)
    conversationIndex: str | None = Field(None, max_length=2048)
    isDeliveryReceiptRequested: bool | None = None
    isReadReceiptRequested: bool | None = None
    isRead: bool | None = None
    isDraft: bool | None = None
    webLink: str | None = Field(None, max_length=2048)
    inferenceClassification: str | None = Field(None, max_length=64)
    body: GraphItemBody
    sender: GraphRecipient | None = None
    from_: GraphRecipient | None = Field(None, alias="from")
    toRecipients: list[GraphRecipient] = Field(default_factory=list, max_length=100)
    ccRecipients: list[GraphRecipient] = Field(default_factory=list, max_length=100)
    bccRecipients: list[GraphRecipient] = Field(default_factory=list, max_length=100)
    replyTo: list[GraphRecipient] = Field(default_factory=list, max_length=100)
    flag: dict[str, Any] | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "from": {
                        "emailAddress": {
                            "address": "akshar@example.org",
                            "name": "Akshar Patel",
                        }
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": "accountant@example.org",
                                "name": "John Accountant",
                            }
                        }
                    ],
                    "receivedDateTime": "2026-05-29T08:12:00Z",
                    "body": {
                        "contentType": "Text",
                        "content": "Attached now.",
                    },
                }
            ]
        },
    )

    @model_validator(mode="after")
    def validate_capture_fields(self) -> "GraphMessage":
        if self.sender is None:
            self.sender = self.from_
        if self.from_ is None:
            self.from_ = self.sender
        if self.sender is None or self.from_ is None:
            raise ValueError("sender or from.emailAddress.address is required")
        if not (self.toRecipients or self.ccRecipients or self.bccRecipients):
            raise ValueError("At least one recipient is required")
        if not (self.receivedDateTime or self.sentDateTime or self.createdDateTime):
            raise ValueError(
                "One timestamp is required: receivedDateTime, sentDateTime, or createdDateTime"
            )
        return self


class GraphSendMailRequest(BaseModel):
    """Microsoft Graph sendMail action request body."""

    message: GraphMessage = Field(
        ...,
        examples=[
            {
                "from": {
                    "emailAddress": {
                        "address": "accountant@example.org",
                        "name": "John Accountant",
                    }
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": "akshar@example.org",
                            "name": "Akshar Patel",
                        }
                    }
                ],
                "sentDateTime": "2026-05-29T08:12:00Z",
                "body": {
                    "contentType": "HTML",
                    "content": "Please send the missing form.",
                },
            }
        ],
    )
    saveToSentItems: bool = True

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "message": {
                        "from": {
                            "emailAddress": {
                                "address": "accountant@example.org",
                                "name": "John Accountant",
                            }
                        },
                        "toRecipients": [
                            {
                                "emailAddress": {
                                    "address": "akshar@example.org",
                                    "name": "Akshar Patel",
                                }
                            }
                        ],
                        "sentDateTime": "2026-05-29T08:12:00Z",
                        "body": {
                            "contentType": "HTML",
                            "content": "Please send the missing form.",
                        },
                    },
                    "saveToSentItems": True,
                }
            ]
        },
    )

    @model_validator(mode="after")
    def validate_sender_not_in_recipients(self) -> "GraphSendMailRequest":
        if not self.message.toRecipients:
            raise ValueError("At least one toRecipient is required for outbound emails")
        sender_address = self.message.from_.emailAddress.address
        recipients = [
            recipient.emailAddress.address
            for recipient in (
                self.message.toRecipients
                + self.message.ccRecipients
                + self.message.bccRecipients
            )
        ]
        if sender_address in recipients:
            raise ValueError("Sender cannot appear in recipients")
        return self


class GraphMessageCollectionResponse(BaseModel):
    """Microsoft Graph collection response shape for messages."""

    odata_context: str = Field(
        "https://graph.microsoft.com/v1.0/$metadata#users('mock')/messages",
        alias="@odata.context",
    )
    value: list[GraphMessage]

    model_config = ConfigDict(populate_by_name=True)


class EmailCaptureResponse(BaseModel):
    """Result of capturing a mock email and enqueueing summary refresh."""

    message: GraphMessage
    summary_task_id: UUID
    summary_task_status: str


EmailAddress = GraphEmailAddress
EmailRecipient = GraphRecipient
EmailSender = GraphRecipient
EmailBody = GraphItemBody
EmailRead = GraphMessage
MockEmailSendRequest = GraphSendMailRequest
MockEmailReceiveRequest = GraphMessage

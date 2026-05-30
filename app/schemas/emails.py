"""Microsoft Graph-compatible email mock schemas."""

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class GraphEmailAddress(BaseModel):
    """Microsoft Graph emailAddress resource."""

    address: EmailStr = Field(..., examples=["akshar@example.org"])
    name: Optional[str] = Field(None, max_length=255, examples=["Akshar Patel"])

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

    odata_type: Optional[str] = Field(None, alias="@odata.type")
    id: Optional[str] = Field(None, max_length=255)
    createdDateTime: Optional[datetime] = None
    lastModifiedDateTime: Optional[datetime] = None
    receivedDateTime: Optional[datetime] = None
    sentDateTime: Optional[datetime] = None
    hasAttachments: Optional[bool] = None
    internetMessageId: Optional[str] = Field(None, max_length=998)
    subject: Optional[str] = Field(None, max_length=512)
    bodyPreview: Optional[str] = Field(None, max_length=1024)
    importance: Optional[str] = Field(None, max_length=32)
    parentFolderId: Optional[str] = Field(None, max_length=255)
    conversationId: Optional[str] = Field(None, max_length=255)
    conversationIndex: Optional[str] = Field(None, max_length=2048)
    isDeliveryReceiptRequested: Optional[bool] = None
    isReadReceiptRequested: Optional[bool] = None
    isRead: Optional[bool] = None
    isDraft: Optional[bool] = None
    webLink: Optional[str] = Field(None, max_length=2048)
    inferenceClassification: Optional[str] = Field(None, max_length=64)
    body: GraphItemBody
    sender: Optional[GraphRecipient] = None
    from_: Optional[GraphRecipient] = Field(None, alias="from")
    toRecipients: List[GraphRecipient] = Field(default_factory=list, max_length=100)
    ccRecipients: List[GraphRecipient] = Field(default_factory=list, max_length=100)
    bccRecipients: List[GraphRecipient] = Field(default_factory=list, max_length=100)
    replyTo: List[GraphRecipient] = Field(default_factory=list, max_length=100)
    flag: Optional[dict[str, Any]] = None

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
    value: List[GraphMessage]

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

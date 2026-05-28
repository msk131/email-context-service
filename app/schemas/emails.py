"""Email mock/send API schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.common.models import EmailDirection


class MockEmailSendRequest(BaseModel):
    """Request to insert a mock email into the email store."""
    client_id: Optional[int] = Field(None, examples=[1])
    client_name: Optional[str] = Field(None, min_length=2, max_length=255, examples=["Akshar Patel"])
    client_email: Optional[EmailStr] = Field(None, examples=["akshar@example.org"])
    direction: EmailDirection = Field(EmailDirection.inbound, examples=[EmailDirection.inbound])
    sender_email: Optional[EmailStr] = Field(None, examples=["akshar@example.org"])
    recipients: Optional[List[EmailStr]] = Field(None, examples=[["accountant@example.org"]])
    subject: str = Field(..., min_length=1, max_length=512, examples=["Missing 1099-INT follow-up"])
    body: str = Field(..., min_length=1, examples=["I received the 1099-INT and attached it."])
    sent_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_client_reference(self) -> "MockEmailSendRequest":
        if self.client_id is None and not (self.client_name and self.client_email):
            raise ValueError("Provide client_id or both client_name and client_email")
        return self


class MockThreadRequest(BaseModel):
    """Request to insert a realistic CPA email thread."""
    client_id: Optional[int] = Field(None, examples=[1])
    client_name: Optional[str] = Field("Akshar Patel", min_length=2, max_length=255)
    client_email: Optional[EmailStr] = Field("akshar@example.org")
    topic: str = Field("1099-INT filing blocker", min_length=2, max_length=120)
    message_count: int = Field(6, ge=2, le=20)

    @model_validator(mode="after")
    def validate_client_reference(self) -> "MockThreadRequest":
        if self.client_id is None and not (self.client_name and self.client_email):
            raise ValueError("Provide client_id or both client_name and client_email")
        return self


class EmailRead(BaseModel):
    """Email response model."""
    id: int
    client_id: int
    sender_accountant_id: Optional[int] = None
    sender_email: EmailStr
    recipients: List[EmailStr]
    subject: str
    body: str
    direction: EmailDirection
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MockThreadResponse(BaseModel):
    """Response for a generated mock thread."""
    client_id: int
    inserted_count: int
    emails: List[EmailRead]

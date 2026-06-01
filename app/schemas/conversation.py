"""Conversation domain validation schemas."""

from typing import List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.summaries import EmailSearchMatch


class ConversationRequest(BaseModel):
    """Question-answer request over accessible email context."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        examples=["What is still blocking Akshar's tax return?"],
    )

    model_config = ConfigDict(extra="forbid")

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3:
            raise ValueError(
                "question must contain at least 3 non-whitespace characters"
            )
        return normalized


class ConversationResponse(BaseModel):
    """Conversational answer grounded in matched emails."""

    question: str = Field(
        ..., max_length=1000, examples=["What is still blocking Akshar's tax return?"]
    )
    answer: str = Field(..., examples=["The main blocker is the missing 1099-INT."])
    source_email_count: int = Field(..., ge=0, examples=[3])
    sources: List[EmailSearchMatch] = Field(default_factory=list)

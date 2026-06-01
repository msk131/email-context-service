"""Conversation API routes."""

from fastapi import APIRouter, Body, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_role
from app.common.rate_limit import CONVERSATION_LIMIT, limiter
from app.common.schemas import Role
from app.db.database import get_session
from app.models.users import User
from app.schemas.conversation import ConversationRequest, ConversationResponse
from app.services.conversation import answer_email_context_question

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post(
    "",
    response_model=ConversationResponse,
    summary="Ask a question about accessible email context",
    description=(
        "Answers a natural-language question using matched emails as source context. "
        "The response includes source email snippets to ground the answer."
    ),
    responses={
        401: {"description": "Missing or invalid bearer token"},
        403: {"description": "Authenticated user does not have the required role"},
        422: {"description": "Invalid request body or date range"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(CONVERSATION_LIMIT)
async def conversation(
    request: Request,
    request_body: ConversationRequest = Body(...),
    current_user: User = Depends(
        require_role(Role.accountant, Role.firm_admin, Role.superuser)
    ),
    session: AsyncSession = Depends(get_session),
) -> ConversationResponse:
    """Question-answer interface over email context."""
    return await answer_email_context_question(
        session,
        current_user=current_user,
        question=request_body.question,
    )

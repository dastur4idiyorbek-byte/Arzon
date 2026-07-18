"""AI chat endpointi (phase 2.4)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import ai
from ..database import get_db
from ..models import User
from ..schemas import ChatMessage, ChatReply
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatReply)
def chat(
    payload: ChatMessage,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    javob = ai.chat_reply(db, user, payload.matn)
    return ChatReply(javob=javob)

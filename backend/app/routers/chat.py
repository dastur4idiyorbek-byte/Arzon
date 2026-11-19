"""AI chat router."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .. import ai
from ..database import get_db
from ..models import User
from ..security import get_current_user

router = APIRouter(prefix="/api", tags=["chat"])

class ChatBody(BaseModel):
    matn: str

@router.post("/chat")
def chat(payload: ChatBody, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {"javob": ai.chat_reply(db, user, payload.matn)}

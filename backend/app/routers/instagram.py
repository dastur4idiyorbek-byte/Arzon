"""Instagram webhook adapted for native ARZON users."""
import os
import httpx
from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import ai
from ..database import SessionLocal
from ..models import User

router = APIRouter(prefix="/webhook/instagram", tags=["instagram"])
VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "")
PAGE_ACCESS_TOKEN = os.getenv("INSTAGRAM_PAGE_TOKEN", "")
GRAPH_URL = "https://graph.facebook.com/v21.0/me/messages"


@router.get("")
def verify(hub_mode: str = Query("", alias="hub.mode"), hub_challenge: str = Query("", alias="hub.challenge"), hub_verify_token: str = Query("", alias="hub.verify_token")):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


def _get_or_create(db: Session, instagram_id: str) -> User:
    user = db.scalar(select(User).where(User.instagram_id == instagram_id))
    if user is None:
        user = User(instagram_id=instagram_id, ism=f"instagram:{instagram_id}")
        db.add(user); db.commit(); db.refresh(user)
    return user


async def _send_dm(recipient_id: str, text: str):
    if PAGE_ACCESS_TOKEN:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(GRAPH_URL, params={"access_token": PAGE_ACCESS_TOKEN}, json={"recipient": {"id": recipient_id}, "message": {"text": text}})


@router.post("")
async def incoming(request: Request):
    body = await request.json()
    for entry in body.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender = messaging.get("sender", {}).get("id")
            text = (messaging.get("message", {}) or {}).get("text")
            if not sender or not text:
                continue
            db = SessionLocal()
            try:
                user = _get_or_create(db, sender)
                answer = ai.chat_reply(db, user, text)
            finally:
                db.close()
            await _send_dm(sender, answer)
    return {"status": "ok"}

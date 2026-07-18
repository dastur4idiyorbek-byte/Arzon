"""Instagram Messaging integratsiyasi — Meta Graph API webhook (phase 6).

Kelgan DM'lar /chat mantig'iga yo'naltiriladi. Instagram foydalanuvchisi uchun
Telegram initData bo'lmagani sabab, alohida "instagram" identifikatori bilan
vaqtinchalik User yaratiladi (telefon tasdiqlash Instagram uchun qo'llanmaydi).
"""
from __future__ import annotations

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
def verify(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
):
    """Webhook tasdiqlash (phase 6.1)."""
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


def _get_or_create_ig_user(db: Session, ig_id: str) -> User:
    # Instagram foydalanuvchisi uchun telegram_id maydonini manfiy hash bilan
    # to'ldiramiz (kolliziyani oldini olish uchun oddiy yechim).
    pseudo_id = -abs(hash(("ig", ig_id))) % (10**15)
    user = db.scalar(select(User).where(User.telegram_id == pseudo_id))
    if user is None:
        user = User(telegram_id=pseudo_id, ism=f"instagram:{ig_id}")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


async def _send_dm(recipient_id: str, text: str) -> None:
    if not PAGE_ACCESS_TOKEN:
        return
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            GRAPH_URL,
            params={"access_token": PAGE_ACCESS_TOKEN},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text},
            },
        )


@router.post("")
async def incoming(request: Request):
    """Kelgan Instagram xabarlarini qabul qiladi va javob yuboradi (phase 6.2)."""
    body = await request.json()
    for entry in body.get("entry", []):
        for messaging in entry.get("messaging", []):
            sender = messaging.get("sender", {}).get("id")
            message = messaging.get("message", {})
            text = message.get("text")
            if not sender or not text:
                continue
            db = SessionLocal()
            try:
                user = _get_or_create_ig_user(db, sender)
                javob = ai.chat_reply(db, user, text)
            finally:
                db.close()
            await _send_dm(sender, javob)
    return {"status": "ok"}

"""Push-bildirishnoma — Expo Push API orqali (Phase 5).

Native ilova (React Native + Expo) foydalanuvchilariga bildirishnoma yuboradi.
Telegram bot foydalanuvchilari xabarni bot orqali oladi; native foydalanuvchilar
esa `users.expo_push_token` bo'yicha push oladi. Ikkalasi birga ishlaydi —
push token bo'lmasa jimgina o'tkazib yuboriladi (xatolik ko'tarilmaydi).
"""
from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from ..models import User

logger = logging.getLogger("arzon.push")

EXPO_URL = "https://exp.host/--/api/v2/push/send"


def _valid(token: str | None) -> bool:
    return bool(token) and (
        token.startswith("ExponentPushToken[") or token.startswith("ExpoPushToken[")
    )


def send_push(
    token: str | None,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """Bitta Expo push token'ga bildirishnoma yuboradi.

    Tarmoq yoki token xatosi butun oqimni to'xtatmasligi kerak — False qaytaradi
    va log qiladi, lekin istisno ko'tarmaydi.
    """
    if not _valid(token):
        return False
    msg = {
        "to": token,
        "title": title,
        "body": body,
        "sound": "default",
        "priority": "high",
    }
    if data:
        msg["data"] = data
    try:
        r = httpx.post(
            EXPO_URL,
            json=msg,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=8,
        )
        if r.status_code != 200:
            logger.warning("Expo push %s: %s", r.status_code, r.text[:200])
            return False
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("Expo push xatolik: %s", e)
        return False


def push_user(
    db: Session,
    user: User | None,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """User obyekti bo'yicha push (token bo'lsa) yuboradi."""
    if user is None:
        return False
    return send_push(user.expo_push_token, title, body, data)


def push_user_id(
    db: Session,
    user_id: int | None,
    title: str,
    body: str,
    data: dict | None = None,
) -> bool:
    """user_id bo'yicha foydalanuvchini topib push yuboradi."""
    if user_id is None:
        return False
    return push_user(db, db.get(User, user_id), title, body, data)

"""Native Expo push notifications."""
import logging
import httpx
from sqlalchemy.orm import Session
from ..models import User

logger = logging.getLogger("arzon.push")
EXPO_URL = "https://exp.host/--/api/v2/push/send"


def _valid(token):
    return bool(token) and (token.startswith("ExponentPushToken[") or token.startswith("ExpoPushToken["))


def send_push(token: str | None, title: str, body: str, data: dict | None = None) -> bool:
    if not _valid(token):
        return False
    message = {"to": token, "title": title, "body": body, "sound": "default", "priority": "high"}
    if data:
        message["data"] = data
    try:
        response = httpx.post(EXPO_URL, json=message, headers={"Content-Type": "application/json", "Accept": "application/json"}, timeout=8)
        return response.status_code == 200
    except Exception as exc:
        logger.warning("Expo push failed: %s", exc)
        return False


def push_user(db: Session, user: User | None, title: str, body: str, data: dict | None = None) -> bool:
    return push_user_id(db, user.id, title, body, data) if user else False


def push_user_id(db: Session, user_id: int | None, title: str, body: str, data: dict | None = None) -> bool:
    if not user_id:
        return False
    user = db.get(User, user_id)
    return send_push(user.expo_push_token, title, body, data) if user else False


def push_admin_ids(db: Session, admin_ids, title: str, body: str, data: dict | None = None) -> int:
    return sum(push_user_id(db, uid, title, body, data) for uid in (admin_ids or []))


def push_store_admins(db: Session, store, title: str, body: str, data: dict | None = None) -> int:
    return push_admin_ids(db, store.admin_ids, title, body, data) if store else 0

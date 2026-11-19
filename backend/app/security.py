"""Native ARZON account authentication and role checks."""
from __future__ import annotations
import hashlib, hmac, json, time
from collections import defaultdict, deque
from typing import Deque
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import Store, User


def get_current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    from .services import auth as auth_service
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    uid = auth_service.decode_token(token) if token else None
    user = db.get(User, uid) if uid is not None else None
    if user is None:
        raise HTTPException(401, "Kirish talab qilinadi.")
    return user


def is_super_admin(user: User) -> bool:
    return bool(user.email and user.email.lower() in settings.super_admin_email_list)


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if not is_super_admin(user):
        raise HTTPException(403, "Faqat super-admin uchun.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> int:
    if is_super_admin(user) or db_has_store(user):
        return user.id
    raise HTTPException(403, "Do'kon administratori huquqi yo'q.")


def db_has_store(user: User) -> bool:
    # Used only as a lightweight identity check; actual store scope is checked per endpoint.
    from .database import SessionLocal
    with SessionLocal() as db:
        return bool(db.scalar(select(Store.id).where(Store.admin_ids.contains([user.id])).limit(1)))


def check_store_access(admin_id: int, store_id: int, db: Session) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(404, "Do'kon topilmadi.")
    if admin_id not in (store.admin_ids or []) and not is_super_admin(db.get(User, admin_id)):
        raise HTTPException(403, "Bu do'konga ruxsatingiz yo'q.")
    return store


def get_admin_store_ids(admin_id: int, db: Session) -> list[int]:
    return [s.id for s in db.scalars(select(Store)).all() if admin_id in (s.admin_ids or [])]


def require_kuryer(user: User = Depends(get_current_user)) -> User:
    if not user.is_kuryer:
        raise HTTPException(403, "Kuryer huquqi yo'q.")
    return user


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit, self.window = limit, window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
    def check(self, key: str) -> bool:
        now = time.monotonic(); q = self._hits[key]
        while q and now - q[0] > self.window: q.popleft()
        if len(q) >= self.limit: return False
        q.append(now); return True
    def reset(self, key: str) -> None: self._hits.pop(key, None)


def enforce_code_rate_limit(key: str) -> None:
    raise HTTPException(410, "Mahfiy kod ARZON 2.0 da mavjud emas.")

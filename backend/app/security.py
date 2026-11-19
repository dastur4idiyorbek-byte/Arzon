"""Native ARZON account authentication and access control."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Store, User


def get_current_user(
    authorization: str = Header(default=""), db: Session = Depends(get_db)
) -> User:
    from .services.auth import decode_token
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    user_id = decode_token(token) if token else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(status_code=401, detail="Kirish talab qilinadi.")
    return user


def is_super_admin(user: User | None) -> bool:
    return bool(user and user.email and user.email.lower() in settings.super_admin_email_list)


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if not is_super_admin(user):
        raise HTTPException(status_code=403, detail="Faqat super-admin uchun.")
    return user


def require_admin(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> int:
    if is_super_admin(user):
        return user.id
    stores = db.scalars(select(Store)).all()
    if any(user.id in (store.admin_ids or []) for store in stores):
        return user.id
    raise HTTPException(status_code=403, detail="Do'kon administratori huquqi yo'q.")


def check_store_access(admin_id: int, store_id: int, db: Session) -> Store:
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Do'kon topilmadi.")
    user = db.get(User, admin_id)
    if admin_id not in (store.admin_ids or []) and not is_super_admin(user):
        raise HTTPException(status_code=403, detail="Bu do'konga ruxsatingiz yo'q.")
    return store


def get_admin_store_ids(admin_id: int, db: Session) -> list[int]:
    return [s.id for s in db.scalars(select(Store)).all() if admin_id in (s.admin_ids or [])]


def require_kuryer(user: User = Depends(get_current_user)) -> User:
    if not (user.is_kuryer or (user.email and user.email.lower() in settings.kuryer_email_list)):
        raise HTTPException(status_code=403, detail="Kuryer huquqi yo'q.")
    return user


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


def enforce_code_rate_limit(key: str) -> None:
    raise HTTPException(status_code=410, detail="Mahfiy kod ARZON 2.0 da mavjud emas.")

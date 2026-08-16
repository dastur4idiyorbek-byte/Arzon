"""Native ilova autentifikatsiyasi — Email/parol, Google, Apple + JWT + rol.

Backend biznes-mantiq o'zgармaydi; bu qatlam native ilова foydalanuvchilarини
JWT sessiya bilan taniydi va rolini (mijoz/admin/moliya/menejer) aniqlaydi.
"""
from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Store, User, _now, admin_identity


# ---------------------------------------------------------------------------
# Parol (bcrypt)
# ---------------------------------------------------------------------------
def hash_password(parol: str) -> str:
    return bcrypt.hashpw(parol.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(parol: str, hash_: str | None) -> bool:
    if not hash_:
        return False
    try:
        return bcrypt.checkpw(parol.encode("utf-8"), hash_.encode("utf-8"))
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# JWT sessiya
# ---------------------------------------------------------------------------
def make_token(user_id: int) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc)
        + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> int | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return int(data["sub"])
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Rol aniqlash (mijoz/admin/moliya/menejer)
# ---------------------------------------------------------------------------
def roles(db: Session, user: User) -> list[str]:
    r = ["mijoz"]
    tid = user.telegram_id
    email = (user.email or "").lower()
    if (tid and tid in settings.super_admin_id_list) or (
        email and email in settings.super_admin_email_list
    ):
        r.append("moliya")
    if (tid and tid in settings.menejer_id_list) or (
        email and email in settings.menejer_email_list
    ):
        r.append("menejer")
    # Do'kon admini: Telegram ID yoki native hisob ID'si (manfiy) admin_ids ичида.
    ident = admin_identity(user)
    stores = db.scalars(select(Store).where(Store.admin_ids.isnot(None))).all()
    if any(ident in (s.admin_ids or []) for s in stores):
        r.append("admin")
    return r


def user_by_admin_id(db: Session, admin_id: int | None) -> User | None:
    """admin_identity() qaytargan raqamdan foydalanuvchini topadi (teskari amal)."""
    if not admin_id:
        return None
    if admin_id < 0:
        return db.get(User, -admin_id)
    return db.scalar(select(User).where(User.telegram_id == admin_id))


# ---------------------------------------------------------------------------
# Email/parol
# ---------------------------------------------------------------------------
def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def register_email(db: Session, email: str, parol: str, ism: str | None) -> User:
    user = User(
        email=email.strip().lower(),
        parol_hash=hash_password(parol),
        ism=(ism or "").strip() or None,
        tel_tasdiqlangan=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Google — id_token'ни Google tokeninfo orqali tekshirish
# ---------------------------------------------------------------------------
def verify_google(id_token: str) -> dict | None:
    try:
        r = httpx.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": id_token},
            timeout=8,
        )
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception:  # noqa: BLE001
        return None
    auds = settings.google_client_id_list
    if auds and data.get("aud") not in auds:
        return None
    if not data.get("sub"):
        return None
    return {"sub": data["sub"], "email": data.get("email"), "ism": data.get("name")}


# ---------------------------------------------------------------------------
# Apple — identity_token JWT imzosini Apple JWKS bilan tekshirish (RS256)
# ---------------------------------------------------------------------------
def verify_apple(identity_token: str) -> dict | None:
    try:
        keys = httpx.get("https://appleid.apple.com/auth/keys", timeout=8).json()["keys"]
        header = jwt.get_unverified_header(identity_token)
        key = next((k for k in keys if k["kid"] == header["kid"]), None)
        if key is None:
            return None
        from jwt.algorithms import RSAAlgorithm

        pub = RSAAlgorithm.from_jwk(json.dumps(key))
        data = jwt.decode(
            identity_token,
            pub,
            algorithms=["RS256"],
            audience=settings.apple_bundle_id,
            issuer="https://appleid.apple.com",
        )
    except Exception:  # noqa: BLE001
        return None
    if not data.get("sub"):
        return None
    return {"sub": data["sub"], "email": data.get("email")}


def oauth_get_or_create(
    db: Session, provider: str, sub: str, email: str | None, ism: str | None
) -> User:
    """Google/Apple sub bo'yicha topadi yoki yaratadi; email bo'yicha bog'laydi."""
    col = User.google_sub if provider == "google" else User.apple_sub
    user = db.scalar(select(User).where(col == sub))
    if user is None and email:
        user = get_by_email(db, email)  # o'sha email bilan avval ro'yxatdan o'tган
    if user is None:
        user = User(ism=(ism or "").strip() or None,
                    email=email.strip().lower() if email else None)
        db.add(user)
    if provider == "google":
        user.google_sub = sub
    else:
        user.apple_sub = sub
    if email and not user.email:
        user.email = email.strip().lower()
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Parolni tiklash (token)
# ---------------------------------------------------------------------------
def make_reset_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(24)
    user.parol_reset_token = token
    user.parol_reset_muddat = _now() + timedelta(hours=1)
    db.commit()
    return token


def reset_password(db: Session, token: str, yangi_parol: str) -> bool:
    from ..models import _as_aware

    user = db.scalar(select(User).where(User.parol_reset_token == token))
    if user is None:
        return False
    if user.parol_reset_muddat and _as_aware(user.parol_reset_muddat) < _now():
        return False
    user.parol_hash = hash_password(yangi_parol)
    user.parol_reset_token = None
    user.parol_reset_muddat = None
    db.commit()
    return True

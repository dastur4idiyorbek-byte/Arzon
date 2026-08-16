"""Native ilova autentifikatsiya endpointlari (Phase 2).

Email/parol, Google, Apple bilan kirish -> JWT sessiya. /me rolни qaytaradi.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_native_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    """Authorization: Bearer <JWT> -> foydalanuvchi."""
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    uid = auth_service.decode_token(token) if token else None
    if uid is None:
        raise HTTPException(status_code=401, detail="Kirish talab qilinadi.")
    user = db.get(User, uid)
    if user is None:
        raise HTTPException(status_code=401, detail="Foydalanuvchi topilmadi.")
    return user


def _auth_response(db: Session, user: User) -> dict:
    return {
        "token": auth_service.make_token(user.id),
        "user": {
            "id": user.id,
            # ARZON ID — foydalanuvchining yagona raqami. Kirish usuli
            # (Telegram/Gmail/Apple) ahamiyatsiz; ruxsatlar shu ID bilan beriladi.
            "arzon_id": user.id,
            "ism": user.ism,
            "email": user.email,
            "tel": user.tel,
            "telegram_id": user.telegram_id,
            "coin_balans": float(user.coin_balans or 0),
        },
        "roles": auth_service.roles(db, user),
    }


# ---------------------------------------------------------------------------
# Email / parol
# ---------------------------------------------------------------------------
class RegisterBody(BaseModel):
    email: str
    parol: str = Field(min_length=6, max_length=128)
    ism: str | None = Field(default=None, max_length=255)


@router.post("/register")
def register(payload: RegisterBody, db: Session = Depends(get_db)):
    if auth_service.get_by_email(db, payload.email):
        raise HTTPException(status_code=409, detail="Bu email allaqachon ro'yxatdan o'tган.")
    user = auth_service.register_email(db, payload.email, payload.parol, payload.ism)
    return _auth_response(db, user)


class LoginBody(BaseModel):
    email: str
    parol: str


@router.post("/login")
def login(payload: LoginBody, db: Session = Depends(get_db)):
    user = auth_service.get_by_email(db, payload.email)
    if user is None or not auth_service.verify_password(payload.parol, user.parol_hash):
        raise HTTPException(status_code=401, detail="Email yoki parol noto'g'ri.")
    return _auth_response(db, user)


# ---------------------------------------------------------------------------
# Google / Apple
# ---------------------------------------------------------------------------
class GoogleBody(BaseModel):
    id_token: str


@router.post("/google")
def google(payload: GoogleBody, db: Session = Depends(get_db)):
    info = auth_service.verify_google(payload.id_token)
    if info is None:
        raise HTTPException(status_code=401, detail="Google tokeni tekshirilmadi.")
    user = auth_service.oauth_get_or_create(
        db, "google", info["sub"], info.get("email"), info.get("ism")
    )
    return _auth_response(db, user)


class AppleBody(BaseModel):
    identity_token: str
    ism: str | None = None


@router.post("/apple")
def apple(payload: AppleBody, db: Session = Depends(get_db)):
    info = auth_service.verify_apple(payload.identity_token)
    if info is None:
        raise HTTPException(status_code=401, detail="Apple tokeni tekshirilmadi.")
    user = auth_service.oauth_get_or_create(
        db, "apple", info["sub"], info.get("email"), payload.ism
    )
    return _auth_response(db, user)


# ---------------------------------------------------------------------------
# Parolni tiklash
# ---------------------------------------------------------------------------
class ForgotBody(BaseModel):
    email: str


@router.post("/forgot")
def forgot(payload: ForgotBody, db: Session = Depends(get_db)):
    user = auth_service.get_by_email(db, payload.email)
    # Xavfsizlik: email topilмаса ham bir xil javob (mavjudlikni oshkor qilmaymiz).
    if user is None or not user.parol_hash:
        return {"ok": True}
    token = auth_service.make_reset_token(db, user)
    # TODO(Phase 2+): email xizmati (Resend) bilan havola yuborish. Hozircha
    # email sozlanмаган -> tokenни qaytaramiz (ilova reset ekranida ishlatadi).
    return {"ok": True, "reset_token": token}


class ResetBody(BaseModel):
    token: str
    yangi_parol: str = Field(min_length=6, max_length=128)


@router.post("/reset")
def reset(payload: ResetBody, db: Session = Depends(get_db)):
    if not auth_service.reset_password(db, payload.token, payload.yangi_parol):
        raise HTTPException(status_code=400, detail="Token noto'g'ri yoki muddati o'tган.")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Joriy foydalanuvchi + rol
# ---------------------------------------------------------------------------
@router.get("/me")
def me(user: User = Depends(get_native_user), db: Session = Depends(get_db)):
    return _auth_response(db, user)

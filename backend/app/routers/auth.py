"""Native authentication endpoints for Email, Google and Apple."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_native_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    uid = auth_service.decode_token(token) if token else None
    user = db.get(User, uid) if uid is not None else None
    if user is None:
        raise HTTPException(401, "Kirish talab qilinadi.")
    return user


def _response(db: Session, user: User) -> dict:
    return {"token": auth_service.make_token(user.id), "user": {
        "id": user.id, "arzon_id": user.id, "ism": user.ism, "email": user.email,
        "tel": user.tel, "is_kuryer": user.is_kuryer,
        "instagram_id": user.instagram_id, "expo_push_token": user.expo_push_token,
    }, "roles": auth_service.roles(db, user)}


class RegisterBody(BaseModel):
    email: str
    parol: str = Field(min_length=6, max_length=128)
    ism: str | None = Field(default=None, max_length=255)


class LoginBody(BaseModel):
    email: str
    parol: str


class GoogleBody(BaseModel):
    id_token: str


class AppleBody(BaseModel):
    identity_token: str
    ism: str | None = None


class ForgotBody(BaseModel):
    email: str


class ResetBody(BaseModel):
    token: str
    yangi_parol: str = Field(min_length=6, max_length=128)


class ProfileUpdate(BaseModel):
    ism: str | None = Field(default=None, max_length=255)
    tel: str | None = Field(default=None, max_length=32)
    expo_push_token: str | None = Field(default=None, max_length=255)


@router.post("/register")
def register(payload: RegisterBody, db: Session = Depends(get_db)):
    if auth_service.get_by_email(db, payload.email):
        raise HTTPException(409, "Bu email allaqachon ro'yxatdan o'tgan.")
    return _response(db, auth_service.register_email(db, payload.email, payload.parol, payload.ism))


@router.post("/login")
def login(payload: LoginBody, db: Session = Depends(get_db)):
    user = auth_service.get_by_email(db, payload.email)
    if user is None or not auth_service.verify_password(payload.parol, user.parol_hash):
        raise HTTPException(401, "Email yoki parol noto'g'ri.")
    return _response(db, user)


@router.post("/google")
def google(payload: GoogleBody, db: Session = Depends(get_db)):
    info = auth_service.verify_google(payload.id_token)
    if info is None:
        raise HTTPException(401, "Google tokeni tekshirilmadi.")
    return _response(db, auth_service.oauth_get_or_create(db, "google", info["sub"], info.get("email"), info.get("ism")))


@router.post("/apple")
def apple(payload: AppleBody, db: Session = Depends(get_db)):
    info = auth_service.verify_apple(payload.identity_token)
    if info is None:
        raise HTTPException(401, "Apple tokeni tekshirilmadi.")
    return _response(db, auth_service.oauth_get_or_create(db, "apple", info["sub"], info.get("email"), payload.ism))


@router.post("/forgot")
def forgot(payload: ForgotBody, db: Session = Depends(get_db)):
    user = auth_service.get_by_email(db, payload.email)
    if user is None or not user.parol_hash:
        return {"ok": True}
    return {"ok": True, "reset_token": auth_service.make_reset_token(db, user)}


@router.post("/reset")
def reset(payload: ResetBody, db: Session = Depends(get_db)):
    if not auth_service.reset_password(db, payload.token, payload.yangi_parol):
        raise HTTPException(400, "Token noto'g'ri yoki muddati o'tgan.")
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_native_user), db: Session = Depends(get_db)):
    return _response(db, user)


@router.patch("/me")
def patch_me(payload: ProfileUpdate, user: User = Depends(get_native_user), db: Session = Depends(get_db)):
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    db.commit(); db.refresh(user)
    return _response(db, user)

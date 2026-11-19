"""Native identity and role helpers."""
from __future__ import annotations
import json, secrets
from datetime import datetime, timedelta, timezone
import bcrypt, httpx, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..config import settings
from ..models import Store, User, _now

def hash_password(password: str) -> str: return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
def verify_password(password: str, hash_: str | None) -> bool:
    try: return bool(hash_) and bcrypt.checkpw(password.encode(), hash_.encode())
    except Exception: return False
def make_token(user_id: int) -> str:
    return jwt.encode({"sub":str(user_id),"exp":datetime.now(timezone.utc)+timedelta(days=settings.jwt_expire_days)},settings.jwt_secret,algorithm="HS256")
def decode_token(token: str) -> int | None:
    try: return int(jwt.decode(token,settings.jwt_secret,algorithms=["HS256"])["sub"])
    except Exception: return None
def roles(db: Session,user: User) -> list[str]:
    result=["mijoz"]
    if user.email and user.email.lower() in settings.super_admin_email_list: result.append("super_admin")
    if user.is_kuryer or (user.email and user.email.lower() in settings.kuryer_email_list): result.append("kuryer")
    if any(user.id in (s.admin_ids or []) for s in db.scalars(select(Store)).all()): result.append("admin")
    return result
def user_by_admin_id(db: Session, user_id: int | None) -> User | None: return db.get(User,user_id) if user_id else None
def get_by_email(db: Session,email: str) -> User | None: return db.scalar(select(User).where(User.email==email.strip().lower()))
def register_email(db: Session,email: str,parol: str,ism: str|None) -> User:
    u=User(email=email.strip().lower(),parol_hash=hash_password(parol),ism=(ism or "").strip() or None)
    if u.email in settings.kuryer_email_list: u.is_kuryer=True
    db.add(u); db.commit(); db.refresh(u); return u
def verify_google(id_token: str) -> dict|None:
    try:
        r=httpx.get("https://oauth2.googleapis.com/tokeninfo",params={"id_token":id_token},timeout=8)
        if r.status_code!=200:return None
        data=r.json()
        if settings.google_client_id_list and data.get("aud") not in settings.google_client_id_list:return None
        return {"sub":data["sub"],"email":data.get("email"),"ism":data.get("name")}
    except Exception:return None
def verify_apple(identity_token: str) -> dict|None:
    try:
        keys=httpx.get("https://appleid.apple.com/auth/keys",timeout=8).json()["keys"]
        header=jwt.get_unverified_header(identity_token); key=next((k for k in keys if k["kid"]==header["kid"]),None)
        if not key:return None
        from jwt.algorithms import RSAAlgorithm
        data=jwt.decode(identity_token,RSAAlgorithm.from_jwk(json.dumps(key)),algorithms=["RS256"],audience=settings.apple_bundle_id,issuer="https://appleid.apple.com")
        return {"sub":data["sub"],"email":data.get("email")}
    except Exception:return None
def oauth_get_or_create(db: Session,provider: str,sub: str,email: str|None,ism: str|None)->User:
    col=User.google_sub if provider=="google" else User.apple_sub
    u=db.scalar(select(User).where(col==sub)) or (get_by_email(db,email) if email else None)
    if u is None:
        u=User(ism=(ism or "").strip() or None,email=email.strip().lower() if email else None);db.add(u)
    setattr(u,"google_sub" if provider=="google" else "apple_sub",sub)
    if email and not u.email:u.email=email.strip().lower()
    if u.email and u.email.lower() in settings.kuryer_email_list:u.is_kuryer=True
    db.commit();db.refresh(u);return u
def make_reset_token(db: Session,user: User)->str:
    token=secrets.token_urlsafe(24);user.parol_reset_token=token;user.parol_reset_muddat=_now()+timedelta(hours=1);db.commit();return token
def reset_password(db: Session,token: str,yangi_parol: str)->bool:
    from ..models import _as_aware
    u=db.scalar(select(User).where(User.parol_reset_token==token))
    if not u or (u.parol_reset_muddat and _as_aware(u.parol_reset_muddat)<_now()):return False
    u.parol_hash=hash_password(yangi_parol);u.parol_reset_token=None;u.parol_reset_muddat=None;db.commit();return True

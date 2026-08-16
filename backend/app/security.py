"""Xavfsizlik: initData tekshiruvi, admin izolyatsiyasi, rate-limit.

Bu modul butun loyihaning xavfsizlik asosidir (working_instructions #2).

Ikki bosqichli tasdiqlash (rule 8):
  1-bosqich — har so'rovda: Telegram initData HMAC-SHA256 imzosi.
  2-bosqich — birinchi buyurtmada: "Kontaktni ulashish" (users.tel_tasdiqlangan).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from collections import defaultdict, deque
from typing import Deque, Dict
from urllib.parse import parse_qsl

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Store, User


# ---------------------------------------------------------------------------
# 1-bosqich: Telegram Mini App initData imzosini tekshirish (phase 3.4)
# ---------------------------------------------------------------------------
def verify_init_data(init_data: str, bot_token: str | None = None) -> dict:
    """initData qatorini tekshiradi va `user` obyektini qaytaradi.

    Telegram algoritmi:
      secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
      hash = HMAC_SHA256(key=secret_key, msg=data_check_string)
    data_check_string — `hash`dan tashqari barcha juftliklar alfavit
    tartibida "key=value\\n" ko'rinishida.

    Xato bo'lsa 401 qaytaradi.
    """
    token = bot_token or settings.initdata_token
    if not token:
        # Token sozlanmagan — imzoni tekshirib bo'lmaydi, xavfsiz tomon: rad et.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData tekshiruvi sozlanmagan (bot token yo'q).",
        )
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData yo'q.",
        )

    # Qiymatlarni saqlagan holda parslash (parse_qsl URL-dekodlaydi).
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData imzosi (hash) yo'q.",
        )

    data_check_string = "\n".join(
        f"{k}={pairs[k]}" for k in sorted(pairs.keys())
    )
    secret_key = hmac.new(
        b"WebAppData", token.encode(), hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData imzosi noto'g'ri.",
        )

    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData ichida user ma'lumoti yo'q.",
        )
    try:
        return json.loads(user_raw)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="initData user ma'lumoti buzuq.",
        )


def get_current_user(
    x_telegram_init_data: str = Header(
        default="", alias="X-Telegram-Init-Data"
    ),
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    """Har bir mijoz-endpoint uchun dependency.

    Ikki usulni qo'llab-quvvatlaydi:
      * Native ilova — `Authorization: Bearer <JWT>` (Phase 2 auth);
      * Telegram Mini App — `X-Telegram-Init-Data` (initData HMAC).
    Foydalanuvchi topiladi/yaratiladi va User obyekti qaytariladi.
    """
    # 1) Native JWT (agar bo'lsa) — ustuvor.
    if authorization.lower().startswith("bearer "):
        from .services import auth as auth_service

        uid = auth_service.decode_token(authorization[7:].strip())
        if uid is not None:
            user = db.get(User, uid)
            if user is not None:
                return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessiya yaroqsiz — qaytadan kiring.",
        )

    # 2) Telegram initData.
    tg_user = verify_init_data(x_telegram_init_data)
    telegram_id = tg_user.get("id")
    if telegram_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram foydalanuvchi ID topilmadi.",
        )

    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        ism = " ".join(
            p for p in [tg_user.get("first_name"), tg_user.get("last_name")] if p
        ).strip() or tg_user.get("username")
        user = User(telegram_id=telegram_id, ism=ism)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Admin izolyatsiyasi (rule 7)
# ---------------------------------------------------------------------------
def is_super_admin(telegram_id: int) -> bool:
    return telegram_id in settings.super_admin_id_list


def check_store_access(admin_id: int, store_id: int, db: Session) -> Store:
    """Admin shu do'konga tegishli ekanini tekshiradi (rule 7).

    Ruxsat bo'lmasa 403 qaytaradi. Super-admin barcha do'konlarga kira oladi.
    Muvaffaqiyatda Store obyektini qaytaradi.
    """
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Do'kon topilmadi.",
        )

    # DIQQAT (Menejer rule 1): super-admin ham oddiy admin kabi — faqat O'Z
    # do'koniga (admin_ids ичида) kiradi. Boshqa do'konга mahsulot yuklolmaydi.
    # Do'kon/admin moderatsiyasi Menejer botда (alohida ruxsat).
    admin_ids = store.admin_ids or []
    if admin_id not in admin_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu do'konga ruxsatingiz yo'q (faqat o'z do'koningiz).",
        )
    return store


def _verify_internal_admin(x_admin_id: str, x_internal_token: str) -> int:
    """Ichki token + X-Admin-Id ni tekshiradi (botlar uchun umumiy qatlam)."""
    if not settings.internal_api_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ichki API tokeni sozlanmagan.",
        )
    if not hmac.compare_digest(x_internal_token, settings.internal_api_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ichki token noto'g'ri.",
        )
    if not x_admin_id.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Admin-Id sarlavhasi noto'g'ri.",
        )
    return int(x_admin_id)


def native_user_or_none(authorization: str, db: Session) -> User | None:
    """`Authorization: Bearer <JWT>` bo'lsa foydalanuvchi, aks holda None.

    Native ilova (React Native) admin/moliya/menejerlari JWT bilan kiradi;
    botlar esa ichki token bilan. Token bor-u yaroqsiz bo'lsa — 401.
    """
    if not authorization.lower().startswith("bearer "):
        return None
    from .services import auth as auth_service

    uid = auth_service.decode_token(authorization[7:].strip())
    user = db.get(User, uid) if uid is not None else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessiya yaroqsiz — qaytadan kiring.",
        )
    return user


def require_admin(
    authorization: str = Header(default=""),
    x_admin_id: str = Header(default="", alias="X-Admin-Id"),
    x_internal_token: str = Header(default="", alias="X-Internal-Token"),
    db: Session = Depends(get_db),
) -> int:
    """Admin endpointlari uchun dependency.

    Ikki kirish usuli:
      * Native ilova — `Authorization: Bearer <JWT>` (do'kon admini roli talab).
      * Boshqaruv Boti — ichki token + X-Admin-Id (telegram_id).

    Qaytadagan qiymat — admin telegram_id (keyin check_store_access tekshiradi,
    rule 7). Bu qatlam faqat "kim" ekanini aniqlaydi va tashqi kirishni to'sadi.
    """
    user = native_user_or_none(authorization, db)
    if user is not None:
        from .services import auth as auth_service

        if "admin" not in auth_service.roles(db, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sizda do'kon administratori huquqi yo'q.",
            )
        # "admin" roli faqat telegram_id biror do'konning admin_ids'ida
        # bo'lganda beriladi — demak bu yerda telegram_id doim mavjud.
        return int(user.telegram_id)
    return _verify_internal_admin(x_admin_id, x_internal_token)


def is_manager(telegram_id: int) -> bool:
    return telegram_id in settings.menejer_id_list


def require_manager(
    authorization: str = Header(default=""),
    x_admin_id: str = Header(default="", alias="X-Admin-Id"),
    x_internal_token: str = Header(default="", alias="X-Internal-Token"),
    db: Session = Depends(get_db),
) -> int:
    """Menejer endpointlari uchun dependency — faqat menejer roli.

    Native ilova (JWT, menejer roli) yoki Menejer Boti (ichki token) qabul
    qilinadi. Boshqaruv Bot bilan hech qanday umumiy kod ulashilmaydi (rule 2).
    """
    user = native_user_or_none(authorization, db)
    if user is not None:
        from .services import auth as auth_service

        if "menejer" not in auth_service.roles(db, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sizda bu botdan foydalanish huquqi yo'q.",
            )
        return int(user.telegram_id or 0)
    admin_id = _verify_internal_admin(x_admin_id, x_internal_token)
    if not is_manager(admin_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sizda bu botdan foydalanish huquqi yo'q.",
        )
    return admin_id


def get_admin_store_ids(admin_id: int, db: Session) -> list[int]:
    """Admin tegishli bo'lgan store_id'lar (admin_ids ичида bo'lganlari).

    Menejer rule 1: super-adminга ham imtiyoz yo'q — u ham faqat o'z
    do'konlarини ko'radi (Boshqaruv botда oddiy admin kabi).
    """
    stores = db.scalars(select(Store)).all()
    return [s.id for s in stores if admin_id in (s.admin_ids or [])]


# ---------------------------------------------------------------------------
# Rate-limit: kod tekshirish urinishlari (phase 3.6)
# ---------------------------------------------------------------------------
class RateLimiter:
    """Oddiy sliding-window rate limiter (jarayon ichida, in-memory).

    Produksiyada Redis'ga o'tkazish tavsiya etiladi, lekin bitta instance
    uchun bu yetarli. Har bir kalit (masalan user_id) bo'yicha oxirgi
    urinishlar vaqtini saqlaydi.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        """True — ruxsat, False — cheklov oshib ketdi."""
        now = time.monotonic()
        q = self._hits[key]
        # Eskirgan urinishlarni tozalash.
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)


code_attempt_limiter = RateLimiter(
    limit=settings.code_attempt_limit,
    window_seconds=settings.code_attempt_window_seconds,
)


def enforce_code_rate_limit(key: str) -> None:
    """Cheklov oshsa 429 qaytaradi."""
    if not code_attempt_limiter.check(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "Juda ko'p urinish. Iltimos, bir daqiqadan so'ng qayta "
                "urinib ko'ring."
            ),
        )

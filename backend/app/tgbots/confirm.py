"""Bir martalik tasdiqlash kodi — moliyaviy amallar uchun (ACOM task_8).

Tasodifiy bosish yoki soxta so'rovlardan himoya. 6 xonali kod chatда
ko'rsatiladi (SMS emas), foydalanuvchi uni QO'LDA yozib yuboradi. 3 daqiqa
amal qiladi, 3 marta noto'g'ri kiritilса so'rov bekor bo'ladi.

Holat context.user_data ичида saqlanadi (bot bitta jarayonда ishlaydi).
"""
from __future__ import annotations

import secrets
import time

_TTL_SECONDS = 180  # 3 daqiqa
_MAX_ATTEMPTS = 3


def issue_code(user_data: dict) -> str:
    """Yangi 6 xonali kod yaratadi va holatда saqlaydi."""
    kod = f"{secrets.randbelow(1_000_000):06d}"
    user_data["_confirm"] = {
        "kod": kod,
        "expires": time.monotonic() + _TTL_SECONDS,
        "attempts": 0,
    }
    return kod


def prompt_text(kod: str) -> str:
    return (
        "🔐 So'rovni tasdiqlash uchun quyidagi kodni yozib yuboring:\n\n"
        f"<b>{kod}</b>\n\n"
        "(Kod 3 daqiqa amal qiladi)"
    )


def check_code(user_data: dict, matn: str) -> str:
    """Kiritilgan kodни tekshiradi.

    Qaytaradi: 'ok' | 'wrong' | 'expired' | 'toomany' | 'yoq'
    'ok' yoki 'toomany' yoki 'expired'да holat tozalanadi.
    """
    state = user_data.get("_confirm")
    if not state:
        return "yoq"
    if time.monotonic() > state["expires"]:
        user_data.pop("_confirm", None)
        return "expired"
    if matn.strip() == state["kod"]:
        user_data.pop("_confirm", None)
        return "ok"
    state["attempts"] += 1
    if state["attempts"] >= _MAX_ATTEMPTS:
        user_data.pop("_confirm", None)
        return "toomany"
    return "wrong"


def clear(user_data: dict) -> None:
    user_data.pop("_confirm", None)

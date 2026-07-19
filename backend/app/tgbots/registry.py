"""Faol bot ilovalari registri.

router.py (webhook), notify.py (buyurtma xabarnomasi) va boshqaruv.py
(mijozga javob yuborish) o'rtasida umumiy holat — sirkulyar importsiz.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from telegram.ext import Application

_apps: dict[str, Application] = {}
# Backend event loop — sync kod (checkout) xabar yuborishни shu loopга topshiradi.
loop: Optional[asyncio.AbstractEventLoop] = None


def register(name: str, app: Application) -> None:
    _apps[name] = app


def get(name: str) -> Optional[Application]:
    return _apps.get(name)


def clear() -> None:
    _apps.clear()


def active() -> list[str]:
    return sorted(_apps.keys())

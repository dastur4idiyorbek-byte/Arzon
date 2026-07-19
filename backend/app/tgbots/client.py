"""Bot handlerlari uchun backend API mijozi (jarayon ichida, localhost).

Webhook rejimida botlar backend bilan BITTA jarayonда ishlaydi — API
chaqiruvlari localhost orqali boradi (tez, tashqi tarmoqsiz).

Eslatma: bots/common.py dagi BackendClient lokal (polling) skriptlar uchun;
bu fayl esa bulutдаги webhook rejimi uchun. Ikkalasi bir xil API'ни chaqiradi.
"""
from __future__ import annotations

import os

import httpx

from ..config import settings


def _self_url() -> str:
    """O'z API manzilimiz — shu jarayon ichidagi server."""
    explicit = os.getenv("BACKEND_SELF_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    port = os.getenv("PORT", "8000")
    return f"http://127.0.0.1:{port}"


class BotApi:
    """Backend API bilan ishlash uchun yupqa qatlam (webhook rejimi)."""

    @property
    def base(self) -> str:
        return _self_url()

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"X-Internal-Token": settings.internal_api_token}
        if extra:
            h.update(extra)
        return h

    async def _request(self, method: str, path: str, **kw) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30) as client:
            return await client.request(method, f"{self.base}{path}", **kw)

    # --- Savdo (mijoz) ---
    async def chat(self, telegram_id: int, matn: str) -> str:
        r = await self._request(
            "POST",
            "/api/bot/chat",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json={"matn": matn},
        )
        if r.status_code == 200:
            return r.json().get("javob", "")
        return "Kechirasiz, hozir javob berolmadim. Keyinroq urinib ko'ring."

    async def confirm_phone(
        self, telegram_id: int, tel: str, ism: str | None = None
    ) -> bool:
        r = await self._request(
            "POST",
            "/api/bot/confirm-phone",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json={"tel": tel, "ism": ism},
        )
        return r.status_code == 200

    async def my_orders(self, telegram_id: int) -> list:
        r = await self._request(
            "GET",
            "/api/bot/orders",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
        )
        return r.json() if r.status_code == 200 else []

    async def loyalty(self, telegram_id: int, bot_username: str = "") -> dict:
        r = await self._request(
            "POST",
            "/api/bot/loyalty",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            params={"bot_username": bot_username},
        )
        return r.json() if r.status_code == 200 else {}

    async def register_referral(
        self, telegram_id: int, referrer_id: int
    ) -> None:
        await self._request(
            "POST",
            "/api/bot/register-referral",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json={"referrer_telegram_id": referrer_id},
        )

    # --- Boshqaruv (admin) ---
    def _admin(self, admin_id: int) -> dict:
        return self._headers({"X-Admin-Id": str(admin_id)})

    async def my_stores(self, admin_id: int) -> list:
        r = await self._request(
            "GET", "/api/admin/my-stores", headers=self._admin(admin_id)
        )
        return r.json() if r.status_code == 200 else []

    async def add_product(
        self, admin_id: int, store_id: int, data: dict
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/products",
            headers=self._admin(admin_id),
            json=data,
        )

    async def list_products(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/products",
            headers=self._admin(admin_id),
        )

    async def orders(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/orders",
            headers=self._admin(admin_id),
        )

    async def confirm_code(self, admin_id: int, kod: str) -> httpx.Response:
        return await self._request(
            "POST",
            "/api/admin/orders/confirm-code",
            headers=self._admin(admin_id),
            json={"kod": kod},
        )

    async def get_secret_code(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/secret-code",
            headers=self._admin(admin_id),
        )

    async def refresh_secret_code(
        self, admin_id: int, store_id: int
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/secret-code/refresh",
            headers=self._admin(admin_id),
        )

    async def stats(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/stats",
            headers=self._admin(admin_id),
        )

    async def top_products(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/top-products",
            headers=self._admin(admin_id),
        )

    async def create_promo(
        self, admin_id: int, store_id: int, data: dict
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/promo",
            headers=self._admin(admin_id),
            json=data,
        )

    async def create_store(self, admin_id: int, data: dict) -> httpx.Response:
        return await self._request(
            "POST",
            "/api/admin/stores",
            headers=self._admin(admin_id),
            json=data,
        )

    async def delete_store(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "DELETE",
            f"/api/admin/stores/{store_id}",
            headers=self._admin(admin_id),
        )


api = BotApi()

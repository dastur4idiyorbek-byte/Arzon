"""Botlar uchun umumiy sozlama va backend API mijozi.

Ikkala bot ham backend'ga ichki token (X-Internal-Token) bilan murojaat qiladi.
Bu botlarni backend bilan bir xil serverda yoki alohida joylashtirish imkonini
beradi — hech qanday token kodga qattiq yozilmaydi.
"""
from __future__ import annotations

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN", "")
SAVDO_BOT_TOKEN = os.getenv("SAVDO_BOT_TOKEN", "")
BOSHQARUV_BOT_TOKEN = os.getenv("BOSHQARUV_BOT_TOKEN", "")
MINIAPP_URL = os.getenv("MINIAPP_URL", "")
SAVDO_BOT_USERNAME = os.getenv("SAVDO_BOT_USERNAME", "")


class BackendClient:
    """Backend API bilan ishlash uchun yupqa qatlam."""

    def __init__(self, base_url: str = BACKEND_URL, token: str = INTERNAL_API_TOKEN):
        self.base_url = base_url
        self.token = token

    def _headers(self, extra: dict | None = None) -> dict:
        h = {"X-Internal-Token": self.token}
        if extra:
            h.update(extra)
        return h

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        async with httpx.AsyncClient(timeout=30) as client:
            return await client.request(
                method, f"{self.base_url}{path}", **kwargs
            )

    # --- Savdo Boti (mijoz kontekstiда) ---
    async def bot_chat(self, telegram_id: int, matn: str) -> str:
        r = await self._request(
            "POST",
            "/api/bot/chat",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json={"matn": matn},
        )
        if r.status_code == 200:
            return r.json().get("javob", "")
        return "Kechirasiz, hozir javob berolmadim. Keyinroq urinib ko'ring."

    async def bot_confirm_phone(
        self, telegram_id: int, tel: str, ism: str | None = None
    ) -> bool:
        r = await self._request(
            "POST",
            "/api/bot/confirm-phone",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json={"tel": tel, "ism": ism},
        )
        return r.status_code == 200

    async def bot_orders(self, telegram_id: int) -> list:
        r = await self._request(
            "GET",
            "/api/bot/orders",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
        )
        return r.json() if r.status_code == 200 else []

    async def bot_loyalty(self, telegram_id: int) -> dict:
        r = await self._request(
            "POST",
            "/api/bot/loyalty",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            params={"bot_username": SAVDO_BOT_USERNAME},
        )
        return r.json() if r.status_code == 200 else {}

    async def bot_register_referral(
        self, telegram_id: int, referrer_id: int
    ) -> None:
        await self._request(
            "POST",
            "/api/bot/register-referral",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json={"referrer_telegram_id": referrer_id},
        )

    # --- Boshqaruv Boti (admin kontekstiда) ---
    def _admin_headers(self, admin_id: int) -> dict:
        return self._headers({"X-Admin-Id": str(admin_id)})

    async def admin_my_stores(self, admin_id: int) -> list:
        r = await self._request(
            "GET", "/api/admin/my-stores", headers=self._admin_headers(admin_id)
        )
        return r.json() if r.status_code == 200 else []

    async def admin_add_product(
        self, admin_id: int, store_id: int, data: dict
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/products",
            headers=self._admin_headers(admin_id),
            json=data,
        )

    async def admin_list_products(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/products",
            headers=self._admin_headers(admin_id),
        )

    async def admin_delete_product(self, admin_id: int, product_id: int) -> httpx.Response:
        return await self._request(
            "DELETE",
            f"/api/admin/products/{product_id}",
            headers=self._admin_headers(admin_id),
        )

    async def admin_orders(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/orders",
            headers=self._admin_headers(admin_id),
        )

    async def admin_confirm_code(self, admin_id: int, kod: str) -> httpx.Response:
        return await self._request(
            "POST",
            "/api/admin/orders/confirm-code",
            headers=self._admin_headers(admin_id),
            json={"kod": kod},
        )

    async def admin_change_status(
        self, admin_id: int, order_id: int, holat: str
    ) -> httpx.Response:
        return await self._request(
            "PATCH",
            f"/api/admin/orders/{order_id}/status",
            headers=self._admin_headers(admin_id),
            json={"holat": holat},
        )

    async def admin_get_secret_code(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/secret-code",
            headers=self._admin_headers(admin_id),
        )

    async def admin_refresh_secret_code(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/secret-code/refresh",
            headers=self._admin_headers(admin_id),
        )

    async def admin_stats(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/stats",
            headers=self._admin_headers(admin_id),
        )

    async def admin_top_products(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/top-products",
            headers=self._admin_headers(admin_id),
        )

    async def admin_create_promo(
        self, admin_id: int, store_id: int, data: dict
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/promo",
            headers=self._admin_headers(admin_id),
            json=data,
        )

    async def super_create_store(self, admin_id: int, data: dict) -> httpx.Response:
        return await self._request(
            "POST",
            "/api/admin/stores",
            headers=self._admin_headers(admin_id),
            json=data,
        )

    async def super_add_admin(
        self, admin_id: int, store_id: int, new_admin_id: int
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/admins",
            headers=self._admin_headers(admin_id),
            json={"admin_telegram_id": new_admin_id},
        )


backend = BackendClient()

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
    async def me(self, telegram_id: int) -> dict:
        r = await self._request(
            "GET",
            "/api/bot/me",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
        )
        return r.json() if r.status_code == 200 else {}

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

    async def order_by_code(self, admin_id: int, kod: str) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/orders/by-code/{kod}",
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

    async def update_product(
        self, admin_id: int, product_id: int, data: dict
    ) -> httpx.Response:
        return await self._request(
            "PATCH",
            f"/api/admin/products/{product_id}",
            headers=self._admin(admin_id),
            json=data,
        )

    async def delete_product(
        self, admin_id: int, product_id: int
    ) -> httpx.Response:
        return await self._request(
            "DELETE",
            f"/api/admin/products/{product_id}",
            headers=self._admin(admin_id),
        )

    async def accept_order(
        self, admin_id: int, order_id: int
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/orders/{order_id}/accept",
            headers=self._admin(admin_id),
        )

    async def cancel_order(
        self, admin_id: int, order_id: int, sabab: str
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/orders/{order_id}/cancel",
            headers=self._admin(admin_id),
            json={"sabab": sabab},
        )

    async def change_status(
        self, admin_id: int, order_id: int, holat: str,
        kuryer_tel: str | None = None,
    ) -> httpx.Response:
        body = {"holat": holat}
        if kuryer_tel:
            body["kuryer_tel"] = kuryer_tel
        return await self._request(
            "PATCH",
            f"/api/admin/orders/{order_id}/status",
            headers=self._admin(admin_id),
            json=body,
        )

    async def search_orders(
        self, admin_id: int, store_id: int, q: str
    ) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/orders/search",
            headers=self._admin(admin_id),
            params={"q": q},
        )

    async def create_self_store(
        self, admin_id: int, nomi: str
    ) -> httpx.Response:
        return await self._request(
            "POST",
            "/api/admin/stores/self",
            headers=self._admin(admin_id),
            json={"nomi": nomi},
        )

    async def add_pickup(
        self, admin_id: int, store_id: int, data: dict
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/pickup-points",
            headers=self._admin(admin_id),
            json=data,
        )

    async def list_pickup(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/pickup-points",
            headers=self._admin(admin_id),
        )

    async def delete_pickup(self, admin_id: int, pp_id: int) -> httpx.Response:
        return await self._request(
            "DELETE",
            f"/api/admin/pickup-points/{pp_id}",
            headers=self._admin(admin_id),
        )

    async def add_store_admin(
        self, admin_id: int, store_id: int, new_admin_id: int
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/admins",
            headers=self._admin(admin_id),
            json={"admin_telegram_id": new_admin_id},
        )

    # --- ACOM coin: mijoz (Savdo) ---
    async def coin_balance(self, telegram_id: int) -> dict:
        r = await self._request(
            "GET",
            "/api/bot/coin/balance",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
        )
        return r.json() if r.status_code == 200 else {}

    async def coin_topup(
        self,
        telegram_id: int,
        summa: float,
        *,
        chek_rasm_url: str | None = None,
        ai_summa: float | None = None,
        ai_sana: str | None = None,
        ai_xulosa: str | None = None,
        tolov_usuli_id: int | None = None,
    ) -> httpx.Response:
        return await self._request(
            "POST",
            "/api/bot/coin/topup",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json={
                "summa": summa,
                "chek_rasm_url": chek_rasm_url,
                "ai_summa": ai_summa,
                "ai_sana": ai_sana,
                "ai_xulosa": ai_xulosa,
                "tolov_usuli_id": tolov_usuli_id,
            },
        )

    async def coin_refund(
        self, telegram_id: int, summa: float, karta: str
    ) -> httpx.Response:
        return await self._request(
            "POST",
            "/api/bot/coin/refund",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json={"summa": summa, "karta_raqami": karta},
        )

    async def coin_tolov_usullari(self, telegram_id: int) -> list:
        r = await self._request(
            "GET",
            "/api/bot/coin/tolov-usullari",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
        )
        return r.json() if r.status_code == 200 else []

    async def dokon_sorovi(self, telegram_id: int, data: dict) -> httpx.Response:
        return await self._request(
            "POST",
            "/api/bot/dokon-sorovi",
            headers=self._headers({"X-Telegram-User-Id": str(telegram_id)}),
            json=data,
        )

    # --- ACOM coin: admin (Boshqaruv) pul yechish ---
    async def store_balance(self, admin_id: int, store_id: int) -> httpx.Response:
        return await self._request(
            "GET",
            f"/api/admin/stores/{store_id}/balance",
            headers=self._admin(admin_id),
        )

    async def withdraw(
        self, admin_id: int, store_id: int, summa: float, karta: str
    ) -> httpx.Response:
        return await self._request(
            "POST",
            f"/api/admin/stores/{store_id}/withdraw",
            headers=self._admin(admin_id),
            json={"summa": summa, "karta_raqami": karta},
        )

    # --- ACOM coin: super-admin (Moliya) ---
    async def moliya_topups(self, admin_id: int, holat: str = "kutilmoqda") -> list:
        r = await self._request(
            "GET", "/api/moliya/topups", headers=self._admin(admin_id),
            params={"holat": holat},
        )
        return r.json() if r.status_code == 200 else []

    async def moliya_topup_approve(self, admin_id: int, sorov_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/topups/{sorov_id}/approve",
            headers=self._admin(admin_id),
        )

    async def moliya_topup_reject(
        self, admin_id: int, sorov_id: int, sabab: str
    ) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/topups/{sorov_id}/reject",
            headers=self._admin(admin_id), json={"sabab": sabab},
        )

    async def moliya_withdraws(self, admin_id: int, holat: str = "kutilmoqda") -> list:
        r = await self._request(
            "GET", "/api/moliya/withdraws", headers=self._admin(admin_id),
            params={"holat": holat},
        )
        return r.json() if r.status_code == 200 else []

    async def moliya_withdraw_paid(self, admin_id: int, sorov_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/withdraws/{sorov_id}/paid",
            headers=self._admin(admin_id),
        )

    async def moliya_refunds(self, admin_id: int, holat: str = "kutilmoqda") -> list:
        r = await self._request(
            "GET", "/api/moliya/refunds", headers=self._admin(admin_id),
            params={"holat": holat},
        )
        return r.json() if r.status_code == 200 else []

    async def moliya_refund_approve(self, admin_id: int, sorov_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/refunds/{sorov_id}/approve",
            headers=self._admin(admin_id),
        )

    async def moliya_refund_reject(
        self, admin_id: int, sorov_id: int, sabab: str
    ) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/refunds/{sorov_id}/reject",
            headers=self._admin(admin_id), json={"sabab": sabab},
        )

    async def moliya_dokon_tolovlari(self, admin_id: int) -> list:
        r = await self._request(
            "GET", "/api/moliya/dokon-tolovlari", headers=self._admin(admin_id)
        )
        return r.json() if r.status_code == 200 else []

    async def moliya_dokon_tolov_confirm(self, admin_id: int, sorov_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/dokon-tolovlari/{sorov_id}/confirm",
            headers=self._admin(admin_id),
        )

    async def moliya_dokon_tolov_reject(self, admin_id: int, sorov_id: int, sabab: str) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/dokon-tolovlari/{sorov_id}/reject",
            headers=self._admin(admin_id), json={"sabab": sabab},
        )

    async def moliya_report(self, admin_id: int) -> dict:
        r = await self._request(
            "GET", "/api/moliya/report", headers=self._admin(admin_id)
        )
        return r.json() if r.status_code == 200 else {}

    async def moliya_get_platforma(self, admin_id: int) -> dict | None:
        r = await self._request(
            "GET", "/api/moliya/platforma-hisob", headers=self._admin(admin_id)
        )
        return r.json() if r.status_code == 200 else None

    async def moliya_set_platforma(
        self, admin_id: int, karta: str, egasi: str
    ) -> httpx.Response:
        return await self._request(
            "POST", "/api/moliya/platforma-hisob",
            headers=self._admin(admin_id),
            json={"karta_raqami": karta, "hisob_egasi": egasi},
        )

    # --- To'lov usullari (Moliya boti) ---
    async def moliya_tolov_usullari(self, admin_id: int) -> list:
        r = await self._request(
            "GET", "/api/moliya/tolov-usullari", headers=self._admin(admin_id)
        )
        return r.json() if r.status_code == 200 else []

    async def moliya_create_tolov(self, admin_id: int, data: dict) -> httpx.Response:
        return await self._request(
            "POST", "/api/moliya/tolov-usullari",
            headers=self._admin(admin_id), json=data,
        )

    async def moliya_update_tolov(
        self, admin_id: int, usul_id: int, data: dict
    ) -> httpx.Response:
        return await self._request(
            "PATCH", f"/api/moliya/tolov-usullari/{usul_id}",
            headers=self._admin(admin_id), json=data,
        )

    async def moliya_toggle_tolov(self, admin_id: int, usul_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/tolov-usullari/{usul_id}/toggle",
            headers=self._admin(admin_id),
        )

    async def moliya_delete_tolov(self, admin_id: int, usul_id: int) -> httpx.Response:
        return await self._request(
            "DELETE", f"/api/moliya/tolov-usullari/{usul_id}",
            headers=self._admin(admin_id),
        )

    # --- Do'kon so'rovlari (Moliya boti) ---
    async def moliya_dokon_sorovlari(self, admin_id: int) -> list:
        r = await self._request(
            "GET", "/api/moliya/dokon-sorovlari", headers=self._admin(admin_id)
        )
        return r.json() if r.status_code == 200 else []

    async def moliya_dokon_approve(self, admin_id: int, sorov_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/dokon-sorovlari/{sorov_id}/approve",
            headers=self._admin(admin_id),
        )

    async def moliya_dokon_reject(
        self, admin_id: int, sorov_id: int, sabab: str
    ) -> httpx.Response:
        return await self._request(
            "POST", f"/api/moliya/dokon-sorovlari/{sorov_id}/reject",
            headers=self._admin(admin_id), json={"sabab": sabab},
        )


    # --- Menejer boti (do'kon/admin/arenda boshqaruvi) ---
    async def menejer_dokon_sorovlari(self, mid: int) -> list:
        r = await self._request("GET", "/api/menejer/dokon-sorovlari", headers=self._admin(mid))
        return r.json() if r.status_code == 200 else []

    async def menejer_dokon_approve(self, mid: int, sorov_id: int) -> httpx.Response:
        # Arenda avtomatik (mahsulot soniga qarab) — summa yuborilmaydi.
        return await self._request(
            "POST", f"/api/menejer/dokon-sorovlari/{sorov_id}/approve",
            headers=self._admin(mid),
        )

    async def menejer_dokon_reject(self, mid: int, sorov_id: int, sabab: str) -> httpx.Response:
        return await self._request(
            "POST", f"/api/menejer/dokon-sorovlari/{sorov_id}/reject",
            headers=self._admin(mid), json={"sabab": sabab},
        )

    async def menejer_adminlar(self, mid: int) -> list:
        r = await self._request("GET", "/api/menejer/adminlar", headers=self._admin(mid))
        return r.json() if r.status_code == 200 else []

    async def menejer_add_admin(self, mid: int, store_id: int, tid: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/menejer/stores/{store_id}/admins",
            headers=self._admin(mid), json={"telegram_id": tid},
        )

    async def menejer_remove_admin(self, mid: int, store_id: int, tid: int) -> httpx.Response:
        return await self._request(
            "DELETE", f"/api/menejer/stores/{store_id}/admins/{tid}",
            headers=self._admin(mid),
        )

    async def menejer_stores(self, mid: int) -> list:
        r = await self._request("GET", "/api/menejer/stores", headers=self._admin(mid))
        return r.json() if r.status_code == 200 else []

    async def menejer_delete_store(self, mid: int, store_id: int) -> httpx.Response:
        return await self._request(
            "DELETE", f"/api/menejer/stores/{store_id}", headers=self._admin(mid)
        )

    async def menejer_store_products(self, mid: int, store_id: int) -> list:
        r = await self._request(
            "GET", f"/api/menejer/stores/{store_id}/products", headers=self._admin(mid)
        )
        return r.json() if r.status_code == 200 else []

    async def menejer_delete_product(self, mid: int, product_id: int) -> httpx.Response:
        return await self._request(
            "DELETE", f"/api/menejer/products/{product_id}", headers=self._admin(mid)
        )

    async def menejer_arenda(self, mid: int) -> list:
        r = await self._request("GET", "/api/menejer/arenda", headers=self._admin(mid))
        return r.json() if r.status_code == 200 else []

    async def menejer_block(self, mid: int, store_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/menejer/stores/{store_id}/block", headers=self._admin(mid)
        )

    async def menejer_unblock(self, mid: int, store_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/menejer/stores/{store_id}/unblock", headers=self._admin(mid)
        )

    async def menejer_arenda_uzaytir(self, mid: int, store_id: int) -> httpx.Response:
        return await self._request(
            "POST", f"/api/menejer/stores/{store_id}/arenda-uzaytir", headers=self._admin(mid)
        )

    async def menejer_report(self, mid: int) -> dict:
        r = await self._request("GET", "/api/menejer/report", headers=self._admin(mid))
        return r.json() if r.status_code == 200 else {}

    async def menejer_broadcast(self, mid: int, target: str, matn: str) -> httpx.Response:
        return await self._request(
            "POST", "/api/menejer/broadcast", headers=self._admin(mid),
            json={"target": target, "matn": matn},
        )


api = BotApi()

"""Loyiha sozlamalari — .env faylidan o'qiladi.

Barcha maxfiy kalitlar (bot tokenlari, Claude API kaliti) shu yerda
markazlashtirilgan. Hech qanday token kodga qattiq yozilmasligi kerak.
"""
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Ma'lumotlar bazasi ---
    # Boshlang'ich bosqichda SQLite, keyin PostgreSQL'ga o'tish mumkin.
    database_url: str = "sqlite:///./arzon.db"

    # --- Telegram botlar ---
    savdo_bot_token: str = ""
    boshqaruv_bot_token: str = ""

    # --- Telegram Mini App / initData tekshiruvi ---
    # initData HMAC imzosi Savdo Boti tokeni asosida tekshiriladi.
    # Odatda savdo_bot_token bilan bir xil, lekin alohida sozlash mumkin.
    miniapp_bot_token: str = ""

    # --- Claude AI ---
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # --- ChromaDB ---
    chroma_persist_dir: str = "./chroma_data"

    # --- Super-admin (loyiha egasi) Telegram ID'lari ---
    # Faqat super-admin yangi do'kon/admin qo'sha oladi (rule 11).
    super_admin_ids: str = ""

    # --- Ichki API tokeni ---
    # Boshqaruv Boti (server tomonda) admin endpointlarга kirishда shu tokenni
    # yuboradi. Bu token internetdan tasodifiy so'rovlarni to'sadi; admin
    # darajasidagi ruxsat esa check_store_access orqali tekshiriladi (rule 7).
    internal_api_token: str = ""

    # --- Xavfsizlik ---
    # Kod tekshirishda urinishlar cheklovi (rule / phase 3.6).
    code_attempt_limit: int = 5
    code_attempt_window_seconds: int = 60

    # Buyurtma kodi amal qilish muddati (kun).
    order_code_ttl_days: int = 14

    # Mini App'ni jonli backend'ga ulash uchun CORS.
    cors_origins: str = "*"

    # --- Majburiy kanalga obuna (Savdo boti onboarding) ---
    # NEWS_CHANNEL_ID: @username yoki -100... raqamli ID. Bo'sh bo'lса — kanal
    # tekshiruvi o'chiq (bot avvalgidek ishlaydi). Bot kanalда admin bo'lishi
    # kerak (getChatMember ishlashi uchun).
    news_channel_id: str = ""
    news_channel_link: str = ""

    @property
    def super_admin_id_list(self) -> List[int]:
        return [
            int(x.strip())
            for x in self.super_admin_ids.split(",")
            if x.strip().isdigit()
        ]

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def initdata_token(self) -> str:
        """initData imzosini tekshirish uchun ishlatiladigan bot tokeni."""
        return self.miniapp_bot_token or self.savdo_bot_token


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

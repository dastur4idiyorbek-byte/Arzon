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
    # Moliya Boti — faqat super-admin (ACOM coin so'rovlarини tasdiqlaydi).
    moliya_bot_token: str = ""
    # Menejer Boti — faqat menejer(lar) (do'kon/admin/arenda boshqaruvi).
    menejer_bot_token: str = ""
    # Menejer Telegram ID'lari (vergul bilan). Faqat ular Menejer botга kiradi.
    menejer_ids: str = ""
    # Boshqaruv (admin) boti username — do'kon ochilgach havola yuboriladi.
    admin_bot_username: str = "arzononlineadmin_bot"
    # Savdo bot username — referal havola uchun (SAVDO_BOT_USERNAME bilan almashtiring).
    savdo_bot_username: str = "arzononline_bot"
    # Do'kon ochish narxi: har 10 mahsulot uchun (som). 10 dona = 100 som.
    dokon_ontalik_narxi: int = 100
    # Arenda muddati tugashiga necha kun qolganda ogohlantirish yuboriladi.
    arenda_ogohlantirish_kunlar: int = 2

    @property
    def menejer_id_list(self) -> List[int]:
        return [
            int(x.strip())
            for x in self.menejer_ids.split(",")
            if x.strip().isdigit()
        ]

    # --- Telegram Mini App / initData tekshiruvi ---
    # initData HMAC imzosi Savdo Boti tokeni asosida tekshiriladi.
    # Odatda savdo_bot_token bilan bir xil, lekin alohida sozlash mumkin.
    miniapp_bot_token: str = ""

    # --- Claude AI (mijoz bilan suhbat — rule 3) ---
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # --- Gemini AI (chek/rasm tahlili — rule 3, alohida kalit) ---
    gemini_api_key: str = ""

    # --- ACOM coin tizimi (barcha summalar KGS, 1 ACOM = 1 KGS) ---
    # Platforma komissiyasi (foiz) — xaridда adminга sof summa tushadi.
    komissiya_foizi: int = 1
    # To'ldirish xavfsizlik chegaralari (KGSда).
    bir_martalik_toldirish_limit: int = 300000
    kunlik_toldirish_soni_limit: int = 3

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

    # Yetkazib berish bazaviy narxi (som, KGS). Hozircha qat'iy 100 som;
    # keyinchalik manzil/masofaga qarab hisoblanadi (hisobla_yetkazish_narxi).
    yetkazish_baza_narxi: int = 100

    # Mini App'ni jonli backend'ga ulash uchun CORS.
    cors_origins: str = "*"

    # --- Majburiy kanalga obuna (Savdo boti onboarding) ---
    # NEWS_CHANNEL_ID: @username yoki -100... raqamli ID. Bo'sh bo'lса — kanal
    # tekshiruvi o'chiq (bot avvalgidek ishlaydi). Bot kanalда admin bo'lishi
    # kerak (getChatMember ishlashi uchun).
    news_channel_id: str = ""
    news_channel_link: str = ""
    # NEWS_CHANNEL_STRICT: "true" bo'lса — a'zolikni tekshirib bo'lmasа
    # (masalan bot kanalда admin emas) mijoz KIRITILMAYDI (fail-closed).
    # Bu majburiy obunani qat'iy qiladi. Standart: "false" (fail-open).
    news_channel_strict: bool = False

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

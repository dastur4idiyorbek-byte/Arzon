"""ARZON backend — FastAPI ilova kirish nuqtasi.

Ishga tushirish:
    cd backend
    uvicorn app.main:app --reload

Jadvallar birinchi ishga tushirishда avtomatik yaratiladi (init_db).
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import admin, bot, chat, instagram, loyalty, media, orders, products

# Telegram webhook botlari — python-telegram-bot o'rnatilgan bo'lsagina.
# (Minimal o'rnatishда backend botlarsiz ham ishlayveradi.)
try:
    from .tgbots import router as tgbots_router
except ImportError:  # noqa: BLE001
    tgbots_router = None


logger = logging.getLogger("arzon.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ishga tushishда jadvallarni yaratamiz (agar mavjud bo'lmasa) + migratsiya.
    init_db()

    # DIQQAT: demo ma'lumotlar ishga tushishда AVTOMATIK qo'shilMAYDI.
    # Demo faqat qo'lда `python backend/seed.py` bilan qo'shiladi (bir martalik).
    # Bu real mahsulotlar restartда demo bilan almashib qolишининг oldini oladi.

    # Produksiyada SQLite ishlatilса — ma'lumotlar saqlanmasligi mumkin (Render
    # diski vaqtinchalik). Aniq ogohlantiramiz.
    from .database import db_url as _effektiv_db

    if _effektiv_db.startswith("sqlite") and (
        os.getenv("RENDER") or os.getenv("RENDER_EXTERNAL_URL")
    ):
        logger.warning(
            "⚠️  DIQQAT: SQLite ishlatilyapti (%s), lekin siz Render'dasiz — "
            "ma'lumotlar har restartда YO'QOLADI! DATABASE_URL ni Neon "
            "(postgresql://...) ga o'rnating.",
            _effektiv_db,
        )

    # Telegram botlarни webhook rejimда yoqamiz (bulutда, PowerShell'siz).
    if tgbots_router is not None:
        await tgbots_router.startup()
    yield
    if tgbots_router is not None:
        await tgbots_router.shutdown()


app = FastAPI(
    title="ARZON API",
    version="0.1.0",
    description="Multi-vendor Telegram/Instagram savdo platformasi",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    faol_botlar = (
        tgbots_router.active_bots() if tgbots_router is not None else []
    )
    return {"status": "ok", "xizmat": "arzon-backend", "botlar": faol_botlar}


# Mijoz endpointlari (Mini App — initData bilan)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(loyalty.router)
# Savdo Boti ichki endpointlari (internal token bilan)
app.include_router(bot.router)
# Admin endpointlari (Boshqaruv Boti — internal token + check_store_access)
app.include_router(admin.router)
# Instagram webhook
app.include_router(instagram.router)
# Telegram rasm proksisi (mahsulot rasmlari Mini App uchun)
app.include_router(media.router)
# Telegram webhook botlari (bulut rejimi)
if tgbots_router is not None:
    app.include_router(tgbots_router.router)

# Mini App statik fayllari — backend orqali xizmat qilinadi.
# Shunда bitta ommaviy manzil (tunnel) bilan ham API (/api/...), ham Mini App
# (/app) ochiladi. Mini App API'ga same-origin (nisbiy) so'rov yuboradi.
# miniapp/ papkasi loyiha ildizида (backend ildizdan --app-dir bilan ishga
# tushiriladi, shuning uchun CWD = ildiz).
if os.path.isdir("miniapp"):
    app.mount(
        "/app",
        StaticFiles(directory="miniapp", html=True),
        name="miniapp",
    )

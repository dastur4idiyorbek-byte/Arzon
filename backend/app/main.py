"""ARZON backend — FastAPI ilova kirish nuqtasi.

Ishga tushirish:
    cd backend
    uvicorn app.main:app --reload

Jadvallar birinchi ishga tushirishда avtomatik yaratiladi (init_db).
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import init_db
from .routers import admin, bot, chat, instagram, loyalty, orders, products


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ishga tushishда jadvallarni yaratamiz (agar mavjud bo'lmasa).
    init_db()
    # SEED_DEMO=1 bo'lса va do'konlar bo'sh bo'lса — demo mahsulotlar qo'shamiz
    # (cloud'da SQLite qayta ishga tushganда tozalangani uchun foydali).
    if os.getenv("SEED_DEMO", "").strip().lower() in ("1", "true", "yes"):
        from .database import SessionLocal
        from .seed_data import seed_if_empty

        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()
    yield


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
    return {"status": "ok", "xizmat": "arzon-backend"}


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

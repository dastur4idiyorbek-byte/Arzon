"""ARZON 2.0 FastAPI application."""
import logging, os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import init_db
from .routers import admin, auth, chat, instagram, media, orders, products
from .routers import super_admin, courier
from .services.daily import start_daily_jobs, stop_daily_jobs
logger = logging.getLogger("arzon.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_daily_jobs()
    yield
    stop_daily_jobs()

app = FastAPI(title="ARZON API", version="2.0.0", description="Native commerce platform", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
@app.get("/health")
def health(): return {"status":"ok", "xizmat":"arzon-backend", "version":"2.0.0"}
for router in (auth.router, products.router, orders.router, chat.router, admin.router, super_admin.router, courier.router, instagram.router, media.router):
    app.include_router(router)

"""ARZON 2.0 FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import auth, products, orders, chat, instagram, media, admin, super_admin, courier
from .services.daily import start_daily_jobs, stop_daily_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_daily_jobs()
    yield
    stop_daily_jobs()


app = FastAPI(title="ARZON API", version="2.0.0", description="Native ARZON commerce platform", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "xizmat": "arzon-backend", "version": "2.0.0"}

for route_module in (
    auth, products, orders, chat, admin, super_admin, courier, instagram, media,
):
    app.include_router(route_module.router)

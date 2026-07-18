"""SQLAlchemy ulanishi va sessiya boshqaruvi.

SQLite (boshlang'ich) va PostgreSQL (produksiya) — ikkalasi ham qo'llab
quvvatlanadi. DATABASE_URL orqali almashtiriladi.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# SQLite bilan ko'p oqimli FastAPI uchun check_same_thread=False kerak.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — har so'rov uchun bitta sessiya."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Barcha jadvallarni yaratadi (agar mavjud bo'lmasa)."""
    from . import models  # noqa: F401  (modellarni ro'yxatga olish uchun)

    Base.metadata.create_all(bind=engine)

"""SQLAlchemy ulanishi va sessiya boshqaruvi.

SQLite (boshlang'ich) va PostgreSQL (produksiya) — ikkalasi ham qo'llab
quvvatlanadi. DATABASE_URL orqali almashtiriladi.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

# Neon/Heroku kabi provayderlar "postgres://" beradi, SQLAlchemy 2.0 esa
# "postgresql://" ni kutadi — normallashtiramiz.
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

is_sqlite = db_url.startswith("sqlite")

# SQLite bilan ko'p oqimli FastAPI uchun check_same_thread=False kerak.
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    # Neon idle ulanishlarni yopadi — eskirган ulanishlarni yangilaymiz.
    pool_recycle=300 if not is_sqlite else -1,
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

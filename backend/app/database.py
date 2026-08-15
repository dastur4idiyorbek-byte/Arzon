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


def _auto_migrate() -> None:
    """Mavjud jadvallarga yetishmayotgan ustunlarni qo'shadi (yengil migratsiya).

    create_all faqat YANGI jadval yaratadi — mavjud jadvalga ustun qo'shmaydi.
    Model'ga yangi maydon qo'shilganда (masalan skidka_foizi), bu funksiya
    ALTER TABLE ... ADD COLUMN bilan uni bazaga qo'shadi. SQLite va Postgres
    ikkalasida ham ishlaydi. Ustunlar nullable qo'shiladi; kod NULL qiymatga
    bardoshli yozilgan (masalan `skidka_foizi or 0`).
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not insp.has_table(table.name):
            continue
        mavjud = {c["name"] for c in insp.get_columns(table.name)}
        for col in table.columns:
            if col.name in mavjud:
                continue
            col_type = col.type.compile(engine.dialect)
            stmt = (
                f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"
            )
            with engine.begin() as conn:
                conn.execute(text(stmt))

    # Native ilova: users.telegram_id endi NULL bo'lishi mumkin (email/OAuth
    # foydalanuvchilarида yo'q). Postgres'да mavjud NOT NULL cheklovини olib
    # tashlaymiz (SQLite'да jadval modeldан yaratilgani uchun shart emas).
    if not is_sqlite and insp.has_table("users"):
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL")
                )
        except Exception:  # noqa: BLE001 — allaqachon nullable bo'lса o'tadi
            pass


def init_db() -> None:
    """Barcha jadvallarni yaratadi (agar mavjud bo'lmasa) va migratsiya qiladi."""
    from . import models  # noqa: F401  (modellarni ro'yxatga olish uchun)

    Base.metadata.create_all(bind=engine)
    _auto_migrate()

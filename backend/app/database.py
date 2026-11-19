"""Database engine and session management."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
is_sqlite = db_url.startswith("sqlite")
engine = create_engine(
    db_url,
    connect_args={"check_same_thread": False} if is_sqlite else {},
    pool_pre_ping=True,
    pool_recycle=300 if not is_sqlite else -1,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _auto_migrate() -> None:
    """Add model columns to existing tables; do not silently drop business data."""
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in existing:
                sql_type = column.type.compile(engine.dialect)
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {sql_type}"))


def init_db() -> None:
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _auto_migrate()

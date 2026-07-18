"""ORM modellar — spec'dagi database_schema bo'limiga aynan mos.

Muhim arxitektura eslatmalari (critical_architecture_rules):
  * stores'da faqat `mahfiy_kirish_kodi` bor — "korinish/havola" maydoni YO'Q
    (rule 2). Do'kon darajasidagi bitta kod butun mahfiy to'plamni ochadi
    (rule 3).
  * products.korinish 'ommaviy' yoki 'mahfiy' bo'ladi — mahsulotga alohida
    kod biriktirilmaydi (rule 3).
  * loyalty_cards / referrals user_id'ga bog'lanadi, store_id'ga emas (rule 9).
  * unlocked_stores mijoz kiritgan kodni saqlaydi; katalog ko'rsatilганда
    joriy kod bilan solishtiriladi (rule 5, rule 6).
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    """Naive datetime'ni UTC deb belgilaydi.

    SQLite timezone'ni saqlamaydi (qiymat naive qaytadi), Postgres esa aware
    qaytaradi. Taqqoslashда ikkalasi ham aware bo'lishi uchun shu yordamchi.
    """
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nomi: Mapped[str] = mapped_column(String(255))
    logo: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # admin_ids — Telegram ID'lar ro'yxati. Portativlik uchun JSON sifatida
    # saqlanadi (SQLite'da massiv turi yo'q; Postgres'da ham JSON ishlaydi).
    # Bazada saqlanadi — .env'dagi statik ro'yxat EMAS (rule 11).
    admin_ids: Mapped[list] = mapped_column(JSON, default=list)
    # Do'konning yagona mahfiy kirish kodi (rule 3). Faqat Boshqaruv Botida
    # yaratiladi/yangilanadi (rule 4).
    mahfiy_kirish_kodi: Mapped[str | None] = mapped_column(
        String(10), nullable=True
    )
    holat: Mapped[str] = mapped_column(String(10), default="faol")

    products: Mapped[list["Product"]] = relationship(
        back_populates="store", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    nomi: Mapped[str] = mapped_column(String(255))
    narxi: Mapped[float] = mapped_column(Numeric(12, 2))
    olcham: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rang: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rasm_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tavsif: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'ommaviy' | 'mahfiy' — mahfiy do'konning kodi orqali ochiladi (rule 3).
    korinish: Mapped[str] = mapped_column(String(10), default="ommaviy")

    store: Mapped["Store"] = relationship(back_populates="products")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True
    )
    ism: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Kontaktni ulashish orqali tasdiqlanadi (rule 8, 2-bosqich).
    tel_tasdiqlangan: Mapped[bool] = mapped_column(Boolean, default=False)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Har bir buyurtma bitta do'konga tegishli — savat store_id bo'yicha
    # ajratiladi (rule 10).
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    mahsulotlar: Mapped[list] = mapped_column(JSON)
    jami_narx: Mapped[float] = mapped_column(Numeric(12, 2))
    holat: Mapped[str] = mapped_column(String(20), default="yangi")
    # 6 xonali takrorlanmas kod (phase 3.1).
    kod: Mapped[str] = mapped_column(String(6), unique=True, index=True)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    # Kod amal qilish muddati (14 kun — phase 3.1).
    amal_qilish_muddati: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tasdiqlangan_vaqt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Kod'ni kim tasdiqlagani (admin telegram_id) — audit uchun (phase 3.3).
    tasdiqlagan_kim: Mapped[int | None] = mapped_column(Integer, nullable=True)


class LoyaltyCard(Base):
    __tablename__ = "loyalty_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    # user_id'ga bog'lanadi — barcha do'konlar bo'yicha umumiy (rule 9).
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    turi: Mapped[str] = mapped_column(String(10))  # 'kumush' | 'oltin'
    kod: Mapped[str | None] = mapped_column(String(10), nullable=True)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Taklif qilingan (yangi) foydalanuvchi.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Taklif qilgan foydalanuvchi.
    referred_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # 'start_bosgan' | 'xarid_qilgan'
    holat: Mapped[str] = mapped_column(String(20), default="start_bosgan")
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_referral_user"),
    )


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Promo do'kon darajasida (rule 9 sodiqlikdan farqli — promo store_id'ga).
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    kod: Mapped[str] = mapped_column(String(32), index=True)
    chegirma_foizi: Mapped[int] = mapped_column(Integer)
    muddat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ishlatilish_soni: Mapped[int] = mapped_column(Integer, default=0)


class UnlockedStore(Base):
    __tablename__ = "unlocked_stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    # Mijoz kiritgan kod. Katalogda joriy stores.mahfiy_kirish_kodi bilan
    # solishtiriladi — mos kelmasa yopiq hisoblanadi (rule 6).
    ishlatilgan_kod: Mapped[str] = mapped_column(String(10))
    ochilgan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )

    __table_args__ = (
        UniqueConstraint("user_id", "store_id", name="uq_unlocked_user_store"),
    )

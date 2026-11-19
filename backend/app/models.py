"""ARZON 2.0 SQLAlchemy models (native-user identity, subscription commerce)."""
from datetime import datetime, timezone
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def _now():
    return datetime.now(timezone.utc)


def _as_aware(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)  # ARZON ID
    ism: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    parol_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    apple_sub: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    parol_reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parol_reset_muddat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_kuryer: Mapped[bool] = mapped_column(Boolean, default=False)
    instagram_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True, nullable=True)
    expo_push_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Media(Base):
    __tablename__ = "media"
    id: Mapped[int] = mapped_column(primary_key=True)
    mime: Mapped[str] = mapped_column(String(64), default="image/jpeg")
    data: Mapped[bytes] = mapped_column(LargeBinary)
    yuklagan_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    maxfiy: Mapped[bool] = mapped_column(Boolean, default=False)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ObunaTarif(Base):
    __tablename__ = "obuna_tariflari"
    id: Mapped[int] = mapped_column(primary_key=True)
    turi: Mapped[str] = mapped_column(String(10), index=True)  # lite|pro|kafe
    nomi: Mapped[str] = mapped_column(String(100))
    mahsulot_limiti: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oylik_narx: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    faol: Mapped[bool] = mapped_column(Boolean, default=True)


class SotuvchiSorovi(Base):
    __tablename__ = "sotuvchi_sorovlari"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sorov_turi: Mapped[str] = mapped_column(String(20), default="yangi")
    tarif_id: Mapped[int | None] = mapped_column(ForeignKey("obuna_tariflari.id", ondelete="SET NULL"), nullable=True)
    tarif_turi: Mapped[str] = mapped_column(String(10), default="lite")
    dokon_turi: Mapped[str] = mapped_column(String(10), default="magazin")
    fish: Mapped[str] = mapped_column(String(255))
    tel: Mapped[str] = mapped_column(String(32))
    dokon_nomi: Mapped[str] = mapped_column(String(255))
    manzil: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ish_vaqti: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dokon_rasm_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    lokatsiya_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lokatsiya_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    pasport_oldi_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pasport_orqa_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    selfi_pasport_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    chek_rasm_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_ochigan_summa: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    ai_xulosasi: Mapped[str | None] = mapped_column(String(32), nullable=True)
    holat: Mapped[str] = mapped_column(String(20), default="kutilmoqda", index=True)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Store(Base):
    __tablename__ = "stores"
    id: Mapped[int] = mapped_column(primary_key=True)
    nomi: Mapped[str] = mapped_column(String(255))
    turi: Mapped[str] = mapped_column(String(10), default="magazin")
    tarif_turi: Mapped[str] = mapped_column(String(10), default="lite")
    logo: Mapped[str | None] = mapped_column(String(512), nullable=True)
    boshqaruvchi_ismi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manzil: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ish_vaqti: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lokatsiya_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lokatsiya_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    ochiq: Mapped[bool] = mapped_column(Boolean, default=True)
    tayyorlanish_vaqti: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yetkazish_rejimi: Mapped[str] = mapped_column(String(20), default="ozi")
    kuryer_narxi: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    admin_ids: Mapped[list] = mapped_column(JSON, default=list)  # User.id values
    tolov_usullari: Mapped[list] = mapped_column(JSON, default=list)
    pasport_oldi_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pasport_orqa_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    selfi_pasport_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    holat: Mapped[str] = mapped_column(String(30), default="faol", index=True)
    mahsulot_limiti: Mapped[int | None] = mapped_column(Integer, nullable=True)
    arenda_muddati_tugashi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    obuna_muddati_tugashi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    products: Mapped[list["Product"]] = relationship(back_populates="store", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    nomi: Mapped[str] = mapped_column(String(255))
    narxi: Mapped[float] = mapped_column(Numeric(12, 2))
    kategoriya: Mapped[str | None] = mapped_column(String(100), nullable=True)
    holat_turi: Mapped[str] = mapped_column(String(20), default="yangi")
    holat_izohi: Mapped[str | None] = mapped_column(Text, nullable=True)
    porsiya: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tayyorlanish_daq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stop_list: Mapped[bool] = mapped_column(Boolean, default=False)
    olcham: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rang: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rasm_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rasm_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    rasm_nisbati: Mapped[str | None] = mapped_column(String(8), default="1:1", nullable=True)
    tavsif: Mapped[str | None] = mapped_column(Text, nullable=True)
    skidka_foizi: Mapped[int] = mapped_column(Integer, default=0)
    yakuniy_narx: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    skidka_muddati: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    miqdor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    store: Mapped["Store"] = relationship(back_populates="products")


class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mahsulotlar: Mapped[list] = mapped_column(JSON)
    jami_narx: Mapped[float] = mapped_column(Numeric(12, 2))
    holat: Mapped[str] = mapped_column(String(30), default="yangi", index=True)
    kod: Mapped[str] = mapped_column(String(6), unique=True, index=True)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    yetkazish_turi: Mapped[str] = mapped_column(String(20), default="kuryer")
    manzil: Mapped[str | None] = mapped_column(String(512), nullable=True)
    kuryer_tel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pickup_point_id: Mapped[int | None] = mapped_column(ForeignKey("pickup_points.id", ondelete="SET NULL"), nullable=True)
    yetkazish_narxi: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    lokatsiya_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lokatsiya_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    oldindan_summa: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    qoldiq_summa: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    qaytarilgan_summa: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    tolov_holati: Mapped[str] = mapped_column(String(20), default="kutilmoqda")
    chek_rasm_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ai_ochigan_summa: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    ai_xulosasi: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tasdiqlangan_vaqt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    kuryer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class PromoCode(Base):
    __tablename__ = "promo_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    kod: Mapped[str] = mapped_column(String(32), index=True)
    chegirma_foizi: Mapped[int] = mapped_column(Integer)
    muddat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ishlatilish_soni: Mapped[int] = mapped_column(Integer, default=0)


class PickupPoint(Base):
    __tablename__ = "pickup_points"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    nomi: Mapped[str] = mapped_column(String(255))
    manzil: Mapped[str] = mapped_column(String(512))
    ish_vaqti: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rasm_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    lokatsiya_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    lokatsiya_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    google_maps_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    holat: Mapped[str] = mapped_column(String(10), default="faol")


class YetkazishHudud(Base):
    __tablename__ = "yetkazish_hududlari"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), nullable=True, index=True)
    hudud_nomi: Mapped[str] = mapped_column(String(255))
    vaqt_oraligi: Mapped[str | None] = mapped_column(String(100), nullable=True)
    boshlanish_soati: Mapped[str | None] = mapped_column(String(10), nullable=True)
    narx: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    faol: Mapped[bool] = mapped_column(Boolean, default=True)


class PlatformaSozlama(Base):
    __tablename__ = "platforma_sozlamalari"
    id: Mapped[int] = mapped_column(primary_key=True)
    faqat_platforma_kuryeri: Mapped[bool] = mapped_column(Boolean, default=False)


class Shikoyat(Base):
    __tablename__ = "shikoyatlar"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    matn: Mapped[str] = mapped_column(Text)
    rasm_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    holat: Mapped[str] = mapped_column(String(20), default="yangi")
    admin_javobi: Mapped[str | None] = mapped_column(Text, nullable=True)


class SotuvchiTolovUsuli(Base):
    __tablename__ = "sotuvchi_tolov_usullari"
    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="CASCADE"), index=True)
    turi: Mapped[str] = mapped_column(String(20))
    nomi: Mapped[str] = mapped_column(String(100))
    qiymat: Mapped[str | None] = mapped_column(Text, nullable=True)
    egasi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qr_rasm_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    faol: Mapped[bool] = mapped_column(Boolean, default=True)


class PlatformaTolovUsuli(Base):
    __tablename__ = "platforma_tolov_usullari"
    id: Mapped[int] = mapped_column(primary_key=True)
    turi: Mapped[str] = mapped_column(String(20))
    nomi: Mapped[str] = mapped_column(String(100))
    qiymat: Mapped[str | None] = mapped_column(Text, nullable=True)
    egasi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qr_rasm_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    faol: Mapped[bool] = mapped_column(Boolean, default=True)
    tartib_raqami: Mapped[int] = mapped_column(Integer, default=0)

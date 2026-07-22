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
    BigInteger,
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
    # Do'kon (admin) kutilayotgan balansi — xariddan tushган sof summa (KGS).
    # Pul yechilганда kamayadi. NULL bardoshli: kodда `or 0`.
    kutilayotgan_balans: Mapped[float | None] = mapped_column(
        Numeric(14, 2), nullable=True, default=0
    )

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
    # Bir nechta rasm (max 10) — /media/<file_id> ko'rinishidagi URL'lar ro'yxati.
    rasm_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Rasm nisbati (Mini App'да ko'rsatish uchun): '1:1','4:3','3:4','9:16','16:9'.
    rasm_nisbati: Mapped[str | None] = mapped_column(
        String(8), nullable=True, default="1:1"
    )
    tavsif: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Chegirma: foiz (0 = yo'q), yakuniy narx (hisoblangan), muddat (ixtiyoriy).
    skidka_foizi: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=0
    )
    yakuniy_narx: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    skidka_muddati: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Ombor: qolgan dona. NULL = cheksiz. 0 = "Tugadi" (sotib bo'lmaydi).
    miqdor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 'ommaviy' | 'mahfiy' — mahfiy do'konning kodi orqali ochiladi (rule 3).
    korinish: Mapped[str] = mapped_column(String(10), default="ommaviy")

    store: Mapped["Store"] = relationship(back_populates="products")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # BigInteger — Telegram ID'lar 2.1 mlrd (INT4) dан oshishi mumkin (Postgres).
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True
    )
    ism: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Kontaktni ulashish orqali tasdiqlanadi (rule 8, 2-bosqich).
    tel_tasdiqlangan: Mapped[bool] = mapped_column(Boolean, default=False)
    # ACOM coin balansi (KGS bilan 1:1). NULL bardoshli: kodда `or 0`.
    coin_balans: Mapped[float | None] = mapped_column(
        Numeric(14, 2), nullable=True, default=0
    )
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
    # Yetkazib berish: 'kuryer' (manzilga) yoki 'pickup' (punktdan olish).
    yetkazish_turi: Mapped[str] = mapped_column(String(10), default="kuryer")
    # Kuryer uchun manzil matni.
    manzil: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Yetkazib berish narxi (som). Manzilga qarab hisoblanadi (hozircha 100).
    yetkazish_narxi: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=0
    )
    # Mijoz yuborgan joylashuv (lokatsiya) — kuryer/punkt uchun.
    lokatsiya_lat: Mapped[float | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    lokatsiya_lng: Mapped[float | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    # Punktdan olish uchun tanlangan punkt.
    pickup_point_id: Mapped[int | None] = mapped_column(
        ForeignKey("pickup_points.id", ondelete="SET NULL"), nullable=True
    )
    tasdiqlangan_vaqt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Kod'ni kim tasdiqlagani (admin telegram_id) — audit uchun (phase 3.3).
    # BigInteger — Telegram ID'lar katta bo'lishi mumkin.
    tasdiqlagan_kim: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    # Bekor qilish sababi (admin kiritadi, mijozga yuboriladi).
    bekor_sababi: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )


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


class PickupPoint(Base):
    __tablename__ = "pickup_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    nomi: Mapped[str] = mapped_column(String(255))
    manzil: Mapped[str] = mapped_column(String(512))
    ish_vaqti: Mapped[str | None] = mapped_column(String(255), nullable=True)
    holat: Mapped[str] = mapped_column(String(10), default="faol")


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


# ===========================================================================
# ACOM coin tizimi (ichki hisob-kitob birligi, 1 ACOM = 1 KGS)
# ===========================================================================
class PlatformaHisob(Base):
    """Platforma biznes karta ma'lumotlari — mijoz balans to'ldirishда o'tkazadi.

    Bitta yozuv (super-admin sozlaydi). Bir nechta bo'lsa oxirgisi ishlatiladi.
    """

    __tablename__ = "platforma_hisob"

    id: Mapped[int] = mapped_column(primary_key=True)
    karta_raqami: Mapped[str] = mapped_column(String(32))
    hisob_egasi: Mapped[str] = mapped_column(String(255))
    yangilangan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )


class PlatformaTolovUsuli(Base):
    """Balans to'ldirish uchun to'lov usullari (super-admin sozlaydi).

    Bir nechta usul: karta, telefon (mobil to'lov), QR kod, crypto hamyon.
    Faqat faol=True usullar mijozларга ko'rinadi (tartib_raqami bo'yicha).
    """

    __tablename__ = "platforma_tolov_usullari"

    id: Mapped[int] = mapped_column(primary_key=True)
    # karta / telefon / qr_kod / crypto
    turi: Mapped[str] = mapped_column(String(20))
    nomi: Mapped[str] = mapped_column(String(50))  # "Optima Bank", "Elsom"...
    # karta raqami / telefon raqami / crypto manzili (QR uchun bo'sh bo'lishi mumkin)
    qiymat: Mapped[str | None] = mapped_column(Text, nullable=True)
    egasi: Mapped[str | None] = mapped_column(String(100), nullable=True)
    qr_rasm_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    izoh: Mapped[str | None] = mapped_column(Text, nullable=True)
    faol: Mapped[bool] = mapped_column(Boolean, default=True)
    tartib_raqami: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)


class CoinToldirishSorovi(Base):
    """Balansni to'ldirish so'rovi — chek rasmi + AI xulosasi bilan."""

    __tablename__ = "coin_toldirish_sorovlari"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    som_summasi: Mapped[float] = mapped_column(Numeric(14, 2))  # KGS
    # Mijoz tanlagan to'lov usuli (yangilanish: bir nechta usul).
    tolov_usuli_id: Mapped[int | None] = mapped_column(
        ForeignKey("platforma_tolov_usullari.id", ondelete="SET NULL"),
        nullable=True,
    )
    chek_rasm_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Gemini Flash o'qigan (TAKLIF — rule 2, yakuniy qaror emas).
    ai_ochigan_summa: Mapped[float | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    ai_ochigan_sana: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # mos_keladi / mos_kelmaydi / aniq_emas
    ai_xulosasi: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # kutilmoqda / tasdiqlandi / rad_etildi
    holat: Mapped[str] = mapped_column(String(20), default="kutilmoqda")
    tasdiqlagan_admin: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    rad_sababi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )


class PulYechishSorovi(Base):
    """Admin (do'kon) pul yechish so'rovi — kutilayotgan balansdan."""

    __tablename__ = "pul_yechish_sorovlari"

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )
    sorolgan_summa: Mapped[float] = mapped_column(Numeric(14, 2))  # KGS
    karta_raqami: Mapped[str] = mapped_column(String(32))
    # kutilmoqda / yopildi / rad_etildi
    holat: Mapped[str] = mapped_column(String(20), default="kutilmoqda")
    soragan_admin: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    yopilgan_vaqt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CoinQaytarishSorovi(Base):
    """Mijoz ishlatilmagan balansini qaytarib olish so'rovi."""

    __tablename__ = "coin_qaytarish_sorovlari"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    sorolgan_summa: Mapped[float] = mapped_column(Numeric(14, 2))  # KGS
    karta_raqami: Mapped[str] = mapped_column(String(32))
    # kutilmoqda / yopildi / rad_etildi
    holat: Mapped[str] = mapped_column(String(20), default="kutilmoqda")
    yaratilgan_vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now
    )
    yopilgan_vaqt: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class CoinHarakati(Base):
    """Barcha coin harakatlari — umumiy tarix (hisobot SUM() bilan hisoblanadi)."""

    __tablename__ = "coin_harakatlari"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    store_id: Mapped[int | None] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # toldirish / xarid / bekor_qilish_qaytarish / pul_yechish /
    # qaytarib_olish / referal_bonus / sodiqlik_bonus / komissiya
    turi: Mapped[str] = mapped_column(String(30), index=True)
    summa: Mapped[float] = mapped_column(Numeric(14, 2))  # KGS
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    vaqt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, index=True
    )

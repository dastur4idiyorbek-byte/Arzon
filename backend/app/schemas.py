"""Pydantic sxemalari — so'rov/javob validatsiyasi."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Mahsulot ---
class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    store_nomi: Optional[str] = None
    nomi: str
    narxi: float
    # Amaldagi sotuv narxi (chegirma hisobga olingan). get_catalog to'ldiradi.
    sotuv_narxi: Optional[float] = None
    olcham: Optional[str] = None
    rang: Optional[str] = None
    rasm_url: Optional[str] = None
    rasm_urls: Optional[list] = None
    rasm_nisbati: Optional[str] = "1:1"
    tavsif: Optional[str] = None
    korinish: str
    skidka_foizi: Optional[int] = 0
    yakuniy_narx: Optional[float] = None
    skidka_muddati: Optional[datetime] = None
    miqdor: Optional[int] = None  # None = cheksiz
    tugadi: Optional[bool] = None


class ProductCreate(BaseModel):
    nomi: str
    narxi: float = Field(ge=0)
    olcham: Optional[str] = None
    rang: Optional[str] = None
    rasm_url: Optional[str] = None
    rasm_urls: Optional[list] = None  # max 10 — routerда tekshiriladi
    rasm_nisbati: Optional[str] = "1:1"
    tavsif: Optional[str] = None
    korinish: str = "ommaviy"  # 'ommaviy' | 'mahfiy'
    skidka_foizi: int = Field(default=0, ge=0, le=99)
    skidka_muddati: Optional[datetime] = None
    miqdor: Optional[int] = Field(default=None, ge=0)


class ProductUpdate(BaseModel):
    nomi: Optional[str] = None
    narxi: Optional[float] = Field(default=None, ge=0)
    olcham: Optional[str] = None
    rang: Optional[str] = None
    rasm_url: Optional[str] = None
    rasm_urls: Optional[list] = None
    rasm_nisbati: Optional[str] = None
    tavsif: Optional[str] = None
    korinish: Optional[str] = None
    skidka_foizi: Optional[int] = Field(default=None, ge=0, le=99)
    skidka_muddati: Optional[datetime] = None
    miqdor: Optional[int] = Field(default=None, ge=0)


# --- Mahfiy kod ---
class UnlockRequest(BaseModel):
    kod: str = Field(min_length=1, max_length=10)


class UnlockResponse(BaseModel):
    ochildi: bool
    store_id: Optional[int] = None
    store_nomi: Optional[str] = None
    qoshilgan_mahsulotlar: int = 0
    xabar: str


# --- Savat / Checkout ---
class CartItem(BaseModel):
    product_id: int
    soni: int = Field(ge=1)
    # Mijoz tanlagan variant (mahsulotда o'lcham/rang ro'yxati bo'lsa).
    olcham: Optional[str] = None
    rang: Optional[str] = None


class PickupPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    nomi: str
    manzil: str
    ish_vaqti: Optional[str] = None


class CheckoutRequest(BaseModel):
    items: List[CartItem]
    promo_kod: Optional[str] = None
    # Yetkazib berish: 'kuryer' (manzil kerak) yoki 'pickup' (punkt kerak).
    yetkazish_turi: str = "kuryer"
    manzil: Optional[str] = None  # kuryer uchun
    # Punktdan olish: {store_id(str): pickup_point_id} — har do'kon uchun punkt.
    pickup_points: Optional[dict] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_id: int
    kod: str
    jami_narx: float
    holat: str
    mahsulotlar: list
    yaratilgan_vaqt: datetime
    amal_qilish_muddati: Optional[datetime] = None
    yetkazish_turi: Optional[str] = "kuryer"
    manzil: Optional[str] = None
    pickup_point_id: Optional[int] = None


class CheckoutResponse(BaseModel):
    # Rule 10: har do'kon uchun alohida buyurtma.
    buyurtmalar: List[OrderOut]
    xabar: str


# --- Kontakt tasdiqlash (rule 8, 2-bosqich) ---
class PhoneConfirmRequest(BaseModel):
    tel: str = Field(min_length=5, max_length=32)


# --- Chat ---
class ChatMessage(BaseModel):
    matn: str


class ChatReply(BaseModel):
    javob: str


# --- Sodiqlik / referal ---
class LoyaltyStatus(BaseModel):
    umumiy_xaridlar: int
    karta_turi: Optional[str] = None
    keyingi_karta_uchun_qolgan: Optional[int] = None
    referal_havola: str
    taklif_qilganlar: int

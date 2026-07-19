"""Demo ma'lumotlar va "bo'sh bo'lsa to'ldirish" funksiyasi.

Cloud'da (Render) SQLite fayli qayta ishga tushganда tozalanadi, shuning uchun
SEED_DEMO=1 bo'lganда backend ishga tushishда demo mahsulotlarni avtomatik
qo'shadi (agar do'konlar hali yo'q bo'lsa). Lokalда ham seed.py shu funksiyani
chaqiradi.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Product, Store
from . import vector_store


DEMO = [
    {
        "nomi": "Zamon Moda",
        "admin_ids": [111111],
        "mahfiy_kirish_kodi": "MODA01",
        "products": [
            {"nomi": "Klassik ko'ylak", "narxi": 180000, "olcham": "M", "rang": "oq", "korinish": "ommaviy",
             "tavsif": "Paxta ko'ylak, kundalik kiyim uchun qulay."},
            {"nomi": "Jinsi shim", "narxi": 250000, "olcham": "32", "rang": "ko'k", "korinish": "ommaviy",
             "tavsif": "Slim-fit jinsi shim."},
            {"nomi": "Limited kolleksiya kurtka", "narxi": 750000, "olcham": "L", "rang": "qora", "korinish": "mahfiy",
             "tavsif": "Cheklangan seriya, faqat maxsus mijozlar uchun."},
        ],
    },
    {
        "nomi": "Texno Bozor",
        "admin_ids": [222222],
        "mahfiy_kirish_kodi": "TEXNO7",
        "products": [
            {"nomi": "Simsiz quloqchin", "narxi": 320000, "rang": "oq", "korinish": "ommaviy",
             "tavsif": "Bluetooth 5.0 quloqchin, shovqinni kamaytirish bilan."},
            {"nomi": "Powerbank 20000mAh", "narxi": 210000, "rang": "qora", "korinish": "ommaviy",
             "tavsif": "Tez quvvatlash, ikki portli powerbank."},
            {"nomi": "Premium smart-soat", "narxi": 1200000, "rang": "kulrang", "korinish": "mahfiy",
             "tavsif": "Yangi model smart-soat, oldindan buyurtma."},
        ],
    },
]


def seed_if_empty(db: Session) -> bool:
    """Do'konlar bo'sh bo'lса demo ma'lumotlarni qo'shadi. True — qo'shildi."""
    if db.scalar(select(Store.id)) is not None:
        return False  # allaqachon ma'lumot bor

    for d in DEMO:
        store = Store(
            nomi=d["nomi"],
            admin_ids=d["admin_ids"],
            mahfiy_kirish_kodi=d["mahfiy_kirish_kodi"],
            holat="faol",
        )
        db.add(store)
        db.flush()
        for p in d["products"]:
            product = Product(store_id=store.id, **p)
            db.add(product)
            db.flush()
            vector_store.index_product(
                product.id, store.id, product.nomi,
                product.tavsif, product.rang, product.korinish,
            )
    db.commit()
    return True

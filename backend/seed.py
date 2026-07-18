"""Demo ma'lumotlar bilan bazani to'ldirish (lokal test uchun).

Ishga tushirish:
    cd backend
    python seed.py

Ikkita do'kon, adminlar va namuna mahsulotlar yaratadi. Mahsulotlar Chroma'ga
ham indekslanadi (agar mavjud bo'lsa). Mavjud demo ma'lumotlar bo'lsa, qayta
yaratmaydi.
"""
from app.database import SessionLocal, init_db
from app.models import Product, Store
from app import vector_store


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


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        if db.query(Store).count() > 0:
            print("Bazада allaqachon do'konlar bor — seed o'tkazib yuborildi.")
            return
        for d in DEMO:
            store = Store(
                nomi=d["nomi"],
                admin_ids=d["admin_ids"],
                mahfiy_kirish_kodi=d["mahfiy_kirish_kodi"],
                holat="faol",
            )
            db.add(store)
            db.flush()  # store.id kerak
            for p in d["products"]:
                product = Product(store_id=store.id, **p)
                db.add(product)
                db.flush()
                vector_store.index_product(
                    product.id, store.id, product.nomi,
                    product.tavsif, product.rang, product.korinish,
                )
            print(
                f"✓ Do'kon '{store.nomi}' (ID {store.id}), "
                f"admin {store.admin_ids}, mahfiy kod {store.mahfiy_kirish_kodi}"
            )
        db.commit()
        print("\nDemo ma'lumotlar tayyor. Mahfiy kodlarni sinab ko'ring: MODA01, TEXNO7")
    finally:
        db.close()


if __name__ == "__main__":
    main()

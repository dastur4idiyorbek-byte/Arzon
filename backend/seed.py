"""Demo ma'lumotlar bilan bazani to'ldirish (lokal test uchun).

Ishga tushirish (loyiha ildizidan):
    python backend/seed.py

Aslida demo ma'lumotlar app/seed_data.py da; bu skript uni chaqiradi.
Do'konlar allaqachon bo'lса — qayta yaratmaydi.
"""
from app.database import SessionLocal, init_db
from app.seed_data import DEMO, seed_if_empty


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        created = seed_if_empty(db)
        if created:
            for d in DEMO:
                print(
                    f"✓ Do'kon '{d['nomi']}', admin {d['admin_ids']}, "
                    f"mahfiy kod {d['mahfiy_kirish_kodi']}"
                )
            print("\nDemo ma'lumotlar tayyor. Mahfiy kodlar: MODA01, TEXNO7")
        else:
            print("Bazада allaqachon do'konlar bor — seed o'tkazib yuborildi.")
    finally:
        db.close()


if __name__ == "__main__":
    main()

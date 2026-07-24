"""ARZON — demo/sinov ma'lumotlarini tozalash (BIR MARTALIK, ehtiyotkorlik bilan).

Ommaviy ishga tushirishдан OLDIN, demo davrida yaratilgan soxta moliyaviy
ma'lumotlarni tozalaydi. Bu QAYTARIB BO'LMAYDIGAN amal.

Xavfsizlik qoidalari (spec):
  1) Avval to'liq ZAXIRA (backup) — skript eslatadi/oladi va tasdiq so'raydi.
  2) DRY RUN (sinov) — nechta qator o'zgarishini FAQAT ko'rsatadi, hech narsa
     o'zgarmaydi. Faqat --execute bilan haqiqiy bajariladi.
  2b) Yakuniy "amalga oshirilsinmi? (ha/yo'q)" tasdiqi.

Ishlatish (backend/ papkasidan):
    python scripts/demo_tozalash.py            # DRY RUN — hech narsa o'zgармaydi
    python scripts/demo_tozalash.py --execute  # haqiqiy tozalash (tasdiq bilan)

Nima tozalanadi:
  - orders, reviews (agar bo'lsa), coin_toldirish_sorovlari,
    pul_yechish_sorovlari, coin_qaytarish_sorovlari, coin_harakatlari — o'chiriladi
  - stores.kutilayotgan_balans -> 0
  - users.coin_balans -> FAQAT referal_bonus yig'indisiga teng (0 EMAS)

Nima TEGILMAYDI:
  - referrals (taklif aloqalari), users, stores, products, admin_ids.
  - Referaldan kelgan coin mukofoti mijoz balansida saqlanadi.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime

# backend/ papkasini import yo'liga qo'shamiz (app.* import qilinishi uchun).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, inspect, select, text  # noqa: E402

from app.database import SessionLocal, db_url, engine, is_sqlite  # noqa: E402
from app.models import CoinHarakati, Store, User  # noqa: E402

# turi='referal_bonus' — referaldан ishlangan coin (saqlanadi).
REFERAL_TURI = "referal_bonus"

# O'chiriladigan jadvallar (tartib muhim emas — FK SET NULL/CASCADE bilan).
# coin_harakatlari ENG OXIRIDA (balans undan hisoblanadi).
DELETE_TABLES = [
    "orders",
    "reviews",  # bu loyihada bo'lmasligi mumkin — mavjud bo'lsagina o'chadi
    "coin_toldirish_sorovlari",
    "pul_yechish_sorovlari",
    "coin_qaytarish_sorovlari",
    "coin_harakatlari",  # OXIRIDA
]


def _table_exists(insp, name: str) -> bool:
    return insp.has_table(name)


def _count(session, table: str) -> int:
    return session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0


def _referal_sums(session) -> dict[int, float]:
    """Har user uchun referal_bonus yig'indisi (coin_harakatlari o'chirilishidan OLDIN)."""
    rows = session.execute(
        select(CoinHarakati.user_id, func.sum(CoinHarakati.summa))
        .where(CoinHarakati.turi == REFERAL_TURI)
        .group_by(CoinHarakati.user_id)
    ).all()
    return {uid: float(s or 0) for uid, s in rows if uid is not None}


def _ask(savol: str) -> bool:
    javob = input(savol + " (ha/yo'q): ").strip().lower()
    return javob in ("ha", "h", "yes", "y")


def _backup(session) -> bool:
    """Zaxira nusxа. SQLite — avtomatik nusxalaydi; Postgres — qo'lда pg_dump."""
    print("\n" + "=" * 60)
    print("1-QADAM: ZAXIRA NUSXA (majburiy!)")
    print("=" * 60)
    if is_sqlite:
        # sqlite:///nisbiy yoki sqlite:////absolut
        path = db_url.split("///", 1)[-1]
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        if not os.path.exists(path):
            print(f"⚠️  SQLite fayli topilmadi: {path}")
            return _ask("Baribir davom etaymi?")
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        dest = f"{path}.backup-{stamp}"
        shutil.copy2(path, dest)
        print(f"✅ SQLite zaxira nusxasi olindi:\n   {dest}")
        return True
    # Postgres (Neon va h.k.) — foydalanuvchi o'zi pg_dump qiladi.
    print("Bu — PostgreSQL bazasi. Iltimos, avval to'liq dump oling, masalan:\n")
    print('   pg_dump "$DATABASE_URL" > arzon-backup-'
          + datetime.now().strftime("%Y%m%d-%H%M%S") + ".sql\n")
    print("Dump tugagach, faylни xavfsiz joyга saqlang.")
    return _ask("Zaxira nusxа olindi va davom etish mumkinmi?")


def dry_run(session) -> dict:
    """Hech narsani o'zgartirmasдан — nima bo'lishini hisoblaydi va ko'rsatadi."""
    insp = inspect(engine)
    counts = {}
    for t in DELETE_TABLES:
        counts[t] = _count(session, t) if _table_exists(insp, t) else None

    ref_sums = _referal_sums(session)
    saqlanadi = {uid: s for uid, s in ref_sums.items() if s > 0}
    jami_users = _count(session, "users")
    referrals_soni = _count(session, "referrals") if _table_exists(insp, "referrals") else 0

    print("\n" + "=" * 60)
    print("DRY RUN — REJALASHTIRILGAN O'ZGARISHLAR (hech narsa o'zgармadi)")
    print("=" * 60)
    print("O'chiriladigan qatorlar:")
    for t in DELETE_TABLES:
        c = counts[t]
        holat = "jadval yo'q" if c is None else f"{c} ta"
        print(f"  • {t:<28} {holat}")
    print("\nBalans:")
    print(f"  • Referal mukofoti saqlanadigan foydalanuvchilar: {len(saqlanadi)} ta "
          f"(jami: {sum(saqlanadi.values()):,.0f} coin)")
    print(f"  • Balansi 0 ga tushadigan foydalanuvchilar: {jami_users - len(saqlanadi)} ta")
    print(f"  • stores.kutilayotgan_balans -> 0 (barcha do'konlar)")
    print("\nTEGILMAYDI:")
    print(f"  • referrals jadvali: {referrals_soni} ta yozuv (o'zgармaydi)")
    print("=" * 60)
    return {"counts": counts, "ref_sums": ref_sums, "saqlanadi": saqlanadi,
            "jami_users": jami_users, "referrals_soni": referrals_soni}


def execute(session, info: dict) -> None:
    """Haqiqiy tozalash — bitta tranzaksiyada (task_1 tartibi bilan)."""
    insp = inspect(engine)
    ref_sums = info["ref_sums"]

    # 1) Balansni referal_bonus yig'индиsiга tenglashtiramiz (0 EMAS) —
    #    coin_harakatlarини o'chirishдан OLDIN.
    for u in session.scalars(select(User)).all():
        u.coin_balans = float(ref_sums.get(u.id, 0) or 0)

    # 2) stores.kutilayotgan_balans -> 0.
    for s in session.scalars(select(Store)).all():
        s.kutilayotgan_balans = 0

    session.flush()

    # 3) Jadvallarni tozalash (coin_harakatlari OXIRIDA — DELETE_TABLES tartibi).
    ochirildi = {}
    for t in DELETE_TABLES:
        if _table_exists(insp, t):
            n = _count(session, t)
            session.execute(text(f"DELETE FROM {t}"))
            ochirildi[t] = n
        else:
            ochirildi[t] = None

    session.commit()

    # 4) Yakuniy hisobot (task_3).
    saqlanadi = info["saqlanadi"]
    print("\n" + "=" * 60)
    print("✅ Tozalash yakunlandi.")
    print("=" * 60)
    print(f"Buyurtmalar o'chirildi: {ochirildi.get('orders') or 0} ta")
    if ochirildi.get("reviews") is not None:
        print(f"Sharhlar o'chirildi: {ochirildi['reviews']} ta")
    toldirish = ochirildi.get("coin_toldirish_sorovlari") or 0
    yechish = ochirildi.get("pul_yechish_sorovlari") or 0
    qaytarish = ochirildi.get("coin_qaytarish_sorovlari") or 0
    print(f"To'ldirish/yechish/qaytarish so'rovlari o'chirildi: "
          f"{toldirish + yechish + qaytarish} ta")
    print(f"Coin harakatlari o'chirildi: {ochirildi.get('coin_harakatlari') or 0} ta")
    print("\nFoydalanuvchilar balansi:")
    print(f"  - {len(saqlanadi)} ta foydalanuvchida referal mukofoti saqlab qolindi "
          f"(jami: {sum(saqlanadi.values()):,.0f} coin)")
    print(f"  - {info['jami_users'] - len(saqlanadi)} ta foydalanuvchining balansi 0 ga tushirildi")
    print(f"\nReferal aloqalari (referrals jadvali): TEGILMADI, "
          f"{info['referrals_soni']} ta yozuv saqlanib qoldi.")
    print("=" * 60)


def main() -> None:
    haqiqiy = "--execute" in sys.argv
    session = SessionLocal()
    try:
        print("ARZON — DEMO MA'LUMOTLARNI TOZALASH")
        print(f"Baza: {'SQLite' if is_sqlite else 'PostgreSQL'}")

        info = dry_run(session)

        if not haqiqiy:
            print("\nℹ️  Bu DRY RUN edi — HECH NARSA o'zgармadi.")
            print("   Haqiqiy tozalash uchun: python scripts/demo_tozalash.py --execute")
            return

        # --execute: zaxira -> yakuniy tasdiq -> bajarish.
        if not _backup(session):
            print("\n❌ Zaxira tasdiqlanmadi — tozalash BEKOR qilindi.")
            return
        print("\n" + "=" * 60)
        print("2-QADAM: YAKUNIY TASDIQ")
        print("=" * 60)
        print("⚠️  Bu amal QAYTARIB BO'LMAYDI. Yuqoridagi qatorlar o'chiriladi.")
        if not _ask("Haqiqatan amalga oshirilsinmi?"):
            print("\n❌ Tozalash BEKOR qilindi (foydalanuvchi tasdiqlamadi).")
            return
        execute(session, info)
    finally:
        session.close()


if __name__ == "__main__":
    main()

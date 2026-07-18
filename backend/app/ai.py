"""Claude AI integratsiyasi — mijozlar uchun chat-yordamchi (phase 2.4).

System prompt ARZON do'koni kontekstini beradi. Mahsulotlar RAG orqali
(vector_store) topilib, kontekstga qo'shiladi. API kaliti bo'lmasa, xushmuomala
zaxira javob qaytariladi (backend baribir ishlaydi).
"""
from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from .config import settings
from .models import User
from .services import catalog as catalog_service
from . import vector_store

_client = None
try:
    if settings.anthropic_api_key:
        import anthropic

        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
except Exception:  # noqa: BLE001
    _client = None


SYSTEM_PROMPT = """Sen — ARZON onlayn savdo platformasining AI yordamchisisan.
ARZON — Telegram va Instagram orqali ishlaydigan ko'p sotuvchili (multi-vendor)
do'kon. Mijoz uchun bu bitta yagona do'kon kabi ko'rinadi.

Vazifang:
- Mijozlarga mahsulot tanlashda yordam berish, savollarga o'zbek tilida,
  samimiy va qisqa javob berish.
- Faqat mijozga ko'rinadigan (kontekstda berilgan) mahsulotlar haqida gapir.
  Kontekstda yo'q mahsulotni o'ylab topma.
- Narx, o'lcham, rang haqida so'ralsa — kontekstdagi ma'lumotdan foydalanish.
- Buyurtma berish uchun mijozni Mini App'dagi katalogga yo'naltir.
- Mahfiy (yashirin) mahsulotlar haqida so'rashsa: ular maxsus kod orqali
  ochilishini, kodni do'kon egasidan olish kerakligini tushuntir. Kodni
  o'zing yaratma yoki taxmin qilma.

Muloyim, foydali va aniq bo'l. Javoblarni qisqa tut."""


def _build_context(products: List[dict]) -> str:
    if not products:
        return "Hozircha mos mahsulot topilmadi."
    lines = []
    for p in products[:10]:
        narx = p.get("narxi")
        line = f"- {p.get('nomi')}"
        if narx is not None:
            line += f" — {narx} so'm"
        if p.get("olcham"):
            line += f", o'lcham: {p['olcham']}"
        if p.get("rang"):
            line += f", rang: {p['rang']}"
        lines.append(line)
    return "Mavjud mahsulotlar:\n" + "\n".join(lines)


def chat_reply(db: Session, user: User, matn: str) -> str:
    """Mijoz xabariga Claude javobini qaytaradi (RAG bilan)."""
    # Mijozga ochiq do'konlar ichidan mos mahsulotlarni topamiz.
    visible_catalog = catalog_service.get_catalog(db, user)
    visible_store_ids = list({p["store_id"] for p in visible_catalog})

    matched = vector_store.search(matn, visible_store_ids, n=5)
    # Vektor natijalarini katalog ma'lumoti bilan boyitamiz.
    by_id = {p["id"]: p for p in visible_catalog}
    context_products = [
        by_id[m["product_id"]]
        for m in matched
        if m.get("product_id") in by_id
    ]
    # Vektor bo'sh bo'lsa — nom bo'yicha oddiy filtrlash (zaxira).
    if not context_products:
        q = matn.lower()
        context_products = [
            p for p in visible_catalog if q in (p["nomi"] or "").lower()
        ][:10] or visible_catalog[:10]

    context = _build_context(context_products)

    if _client is None:
        # Zaxira javob (API kaliti yo'q).
        return (
            "Salom! Hozircha AI yordamchi to'liq ulanmagan, lekin sizga "
            "yordam bera olaman.\n\n" + context
        )

    try:
        resp = _client.messages.create(
            model=settings.claude_model,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Kontekst:\n{context}\n\n"
                        f"Mijoz savoli: {matn}"
                    ),
                }
            ],
        )
        return "".join(
            block.text for block in resp.content if block.type == "text"
        )
    except Exception as e:  # noqa: BLE001
        return (
            "Kechirasiz, hozir javob berishda muammo bo'ldi. "
            f"Keyinroq urinib ko'ring.\n\n{context}"
        )

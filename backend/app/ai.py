"""AI chat-yordamchi — Gemini (bepul) yoki Claude (phase 2.4).

Provayder tanlash:
  * GEMINI_API_KEY berilса — Google Gemini (bepul tier) ishlatiladi.
  * Aks holda ANTHROPIC_API_KEY berilса — Anthropic Claude.
  * Hech biri bo'lmasa — xushmuomala zaxira javob (backend baribir ishlaydi).

Mahsulotlar RAG orqali (vector_store) topilib, kontekstga qo'shiladi.
"""
from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .config import settings
from .models import User
from .services import catalog as catalog_service
from . import vector_store

# .env ni os.environ ga yuklaymiz — GEMINI_API_KEY ni o'qish uchun
# (backend config'i pydantic-settings orqali ishlaydi, lekin Gemini kalitini
#  shu yerda to'g'ridan-to'g'ri o'qiymiz — config.py'ni o'zgartirmasdan).
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# --- Gemini klienti (google-genai SDK) ---
_gemini = None
try:
    if GEMINI_API_KEY:
        from google import genai

        _gemini = genai.Client(api_key=GEMINI_API_KEY)
except Exception:  # noqa: BLE001
    _gemini = None

# --- Claude klienti ---
_claude = None
try:
    if settings.anthropic_api_key:
        import anthropic

        _claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)
except Exception:  # noqa: BLE001
    _claude = None


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


def _fallback(context: str) -> str:
    return (
        "Salom! Hozircha AI yordamchi to'liq ulanmagan, lekin sizga "
        "yordam bera olaman.\n\n" + context
    )


def chat_reply(db: Session, user: User, matn: str) -> str:
    """Mijoz xabariga AI javobini qaytaradi (RAG bilan)."""
    # Mijozga ochiq do'konlar ichidan mos mahsulotlarni topamiz.
    visible_catalog = catalog_service.get_catalog(db, user)
    visible_store_ids = list({p["store_id"] for p in visible_catalog})

    matched = vector_store.search(matn, visible_store_ids, n=5)
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
    prompt = f"Kontekst:\n{context}\n\nMijoz savoli: {matn}"

    # 1) Gemini (bepul)
    if _gemini is not None:
        try:
            from google.genai import types

            resp = _gemini.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    max_output_tokens=600,
                ),
            )
            text = (resp.text or "").strip()
            return text or _fallback(context)
        except Exception:  # noqa: BLE001
            pass  # Gemini ishlamasa — quyidagilarga o'tamiz

    # 2) Claude
    if _claude is not None:
        try:
            resp = _claude.messages.create(
                model=settings.claude_model,
                max_tokens=600,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                block.text for block in resp.content if block.type == "text"
            )
        except Exception:  # noqa: BLE001
            pass

    # 3) Zaxira javob (AI ulanmagan)
    return _fallback(context)

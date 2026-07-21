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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") or settings.gemini_api_key
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
            line += f" — {narx} som"
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


# ===========================================================================
# Chek/rasm tahlili — Gemini Flash (ACOM coin, rule 2 & rule 3)
# ===========================================================================
# DIQQAT (rule 2): bu funksiya faqat TAKLIF beradi — yakuniy qarorni HAR DOIM
# super-admin Moliya Botида tugma bosib beradi. AI "mos" desa ham coin
# avtomatik berilmaydi.
def analyze_receipt(
    image_bytes: bytes, mime_type: str, kutilgan_summa: float
) -> dict:
    """Chek rasmidan summa va sanani o'qiydi (Gemini Flash).

    Qaytaradi: {"summa": float|None, "sana": str|None, "xulosa": str}
    xulosa: 'mos_keladi' | 'mos_kelmaydi' | 'aniq_emas'
    Barcha summalar Qirg'iziston somida (KGS).
    """
    natija = {"summa": None, "sana": None, "xulosa": "aniq_emas"}
    if _gemini is None or not image_bytes:
        return natija  # AI yo'q — super-admin qo'lда tekshiradi (rule 2)

    try:
        import json as _json

        from google.genai import types

        prompt = (
            "Bu bank o'tkazmasi/to'lov cheki rasmi. Undan quyidagilarни ajratib ol:\n"
            "- summa: o'tkazilgan pul miqdori (faqat son, Qirg'iziston somida, "
            "vergul/probelsiz)\n"
            "- sana: to'lov sanasi va vaqti (matn ko'rinishida)\n\n"
            "Faqat JSON qaytar, boshqa matnsiz: "
            '{"summa": <son yoki null>, "sana": "<matn yoki null>"}'
        )
        resp = _gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            config=types.GenerateContentConfig(max_output_tokens=300),
        )
        text = (resp.text or "").strip()
        # JSON blokни ajratib olamiz (```json ... ``` bo'lishi mumkin).
        if "{" in text and "}" in text:
            text = text[text.index("{") : text.rindex("}") + 1]
        parsed = _json.loads(text)
        summa = parsed.get("summa")
        sana = parsed.get("sana")
        if summa is not None:
            try:
                summa = float(str(summa).replace(" ", "").replace(",", ""))
            except (ValueError, TypeError):
                summa = None
        natija["summa"] = summa
        natija["sana"] = str(sana) if sana else None
        # Mijoz kiritgan summa bilan solishtiramiz (1 som farqга yo'l qo'yamiz).
        if summa is None:
            natija["xulosa"] = "aniq_emas"
        elif abs(summa - float(kutilgan_summa)) <= 1:
            natija["xulosa"] = "mos_keladi"
        else:
            natija["xulosa"] = "mos_kelmaydi"
    except Exception:  # noqa: BLE001
        natija["xulosa"] = "aniq_emas"
    return natija

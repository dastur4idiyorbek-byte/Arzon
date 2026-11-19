"""ARZON 2.0 AI chat and receipt analysis with Telegram removed."""
from __future__ import annotations
import json, os
from typing import List

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from .config import settings
from .models import User

load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "") or settings.gemini_api_key
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
_gemini = None
_claude = None
try:
    if GEMINI_KEY:
        from google import genai
        _gemini = genai.Client(api_key=GEMINI_KEY)
except Exception:
    _gemini = None
try:
    if settings.anthropic_api_key:
        import anthropic
        _claude = anthropic.Anthropic(api_key=settings.anthropic_api_key)
except Exception:
    _claude = None

SYSTEM = "Sen ARZON mobil ilovasi uchun o'zbek tilida qisqa, samimiy savdo yordamchisisan. Faqat berilgan mahsulotlar haqida gapir."


def chat_reply(db: Session, user: User, matn: str) -> str:
    from sqlalchemy import select
    from .models import Product, Store
    products = db.scalars(select(Product).join(Store, Store.id == Product.store_id).where(Store.holat == "faol").limit(10)).all()
    context = "Mavjud mahsulotlar:\n" + "\n".join(f"- {p.nomi}: {float(p.narxi)} som" for p in products)
    prompt = context + "\nMijoz savoli: " + matn
    if _gemini:
        try:
            from google.genai import types
            response = _gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt,
                config=types.GenerateContentConfig(system_instruction=SYSTEM, max_output_tokens=600))
            if response.text:
                return response.text.strip()
        except Exception:
            pass
    if _claude:
        try:
            response = _claude.messages.create(model=settings.claude_model, max_tokens=600,
                system=SYSTEM, messages=[{"role": "user", "content": prompt}])
            return "".join(block.text for block in response.content if block.type == "text")
        except Exception:
            pass
    return "Salom! " + (context if context != "Mavjud mahsulotlar:\n" else "Hozircha mahsulot topilmadi.")


def analyze_receipt(image_bytes: bytes, mime_type: str, kutilgan_summa: float) -> dict:
    result = {"summa": None, "sana": None, "xulosa": "aniq_emas"}
    if not _gemini or not image_bytes:
        return result
    try:
        from google.genai import types
        prompt = ('Bu to\'lov cheki. Faqat JSON qaytar: {"summa": <son yoki null>, "sana": "<matn yoki null>"}')
        response = _gemini.models.generate_content(model=GEMINI_MODEL,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), prompt],
            config=types.GenerateContentConfig(max_output_tokens=300))
        text = (response.text or "").strip()
        if "{" in text and "}" in text:
            text = text[text.index("{"):text.rindex("}") + 1]
        parsed = json.loads(text)
        summa = parsed.get("summa")
        if summa is not None:
            summa = float(str(summa).replace(" ", "").replace(",", ""))
        result["summa"] = summa
        result["sana"] = parsed.get("sana")
        result["xulosa"] = "mos_keladi" if summa is not None and abs(summa - float(kutilgan_summa)) <= 1 else ("mos_kelmaydi" if summa is not None else "aniq_emas")
    except Exception:
        result["xulosa"] = "aniq_emas"
    return result

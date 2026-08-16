"""Telegram rasm proksisi — /media/{file_id}.

Admin mahsulot rasmini Boshqaruv Botiga yuboradi; Telegram bizga file_id
beradi. Mini App'да rasmni ko'rsatish uchun bu endpoint file_id'ни Telegram
serveridан olib, oqim sifatida qaytaradi. Bot tokeni URLда oshkor bo'lmaydi
(to'g'ridan-to'g'ri Telegram file URL ishlatilsa token ko'rinib qolаrdi).

Telegram file_path ~1 soatда eskiradi, shuning uchun har so'rovда getFile
chaqiriladi; javob esa brauzerда 1 kun keshlanadi.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Media
from ..security import require_admin

router = APIRouter(tags=["media"])

_TG_API = "https://api.telegram.org"

# Ilovadan yuklanadigan rasm uchun chegara (siqilgan rasm bundan ancha kichik).
MAX_RASM_BAYT = 8 * 1024 * 1024


# ---------------------------------------------------------------------------
# Ilovadan rasm yuklash (kamera/galereya) — bazada saqlanadi
# ---------------------------------------------------------------------------
# DIQQAT: bu yo'l `/media/{file_id}` dan OLDIN turishi shart — aks holda
# "db" so'zi file_id deb qabul qilinadi (FastAPI yo'llarni tartib bo'yicha
# tekshiradi).
@router.get("/media/db/{media_id}")
def media_db(media_id: int, db: Session = Depends(get_db)):
    """Bazada saqlangan rasmni beradi."""
    m = db.get(Media, media_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Rasm topilmadi.")
    return Response(
        content=m.data,
        media_type=m.mime or "image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/api/media/upload")
async def media_upload(
    rasm: UploadFile = File(...),
    admin_id: int = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Ilovadan rasm yuklash (mahsulot rasmi uchun).

    Faqat do'kon admini yuklay oladi. Qaytaradi: {"url": "/media/db/<id>"} —
    shu qiymat mahsulotning `rasm_url` maydoniga yoziladi.
    """
    raw = await rasm.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Rasm bo'sh.")
    if len(raw) > MAX_RASM_BAYT:
        raise HTTPException(
            status_code=413,
            detail="Rasm juda katta (8 MB dan oshmasin).",
        )
    mime = (rasm.content_type or "image/jpeg").lower()
    if not mime.startswith("image/"):
        raise HTTPException(status_code=400, detail="Faqat rasm yuklash mumkin.")

    m = Media(mime=mime, data=raw, yuklagan_admin=admin_id)
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"url": f"/media/db/{m.id}", "id": m.id}


@router.get("/media/{file_id}")
async def media(file_id: str):
    # Rasm turli botlarga yuborilishi mumkin: mahsulot rasmi -> Boshqaruv,
    # to'ldirish cheki -> Savdo boti. file_id bot tokeniga bog'liq, shuning
    # uchun mavjud tokenlarни navbat bilan sinaymiz (birinchi ishlaganи).
    tokens = [
        t
        for t in (
            settings.boshqaruv_bot_token,
            settings.savdo_bot_token,
            settings.moliya_bot_token,
        )
        if t
    ]
    # Takrorlarни olib tashlaymiz (tartibни saqlab).
    seen: set[str] = set()
    tokens = [t for t in tokens if not (t in seen or seen.add(t))]
    if not tokens or len(file_id) > 200:
        raise HTTPException(status_code=404, detail="Rasm topilmadi.")

    file_path = None
    token = None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            for t in tokens:
                r = await client.get(
                    f"{_TG_API}/bot{t}/getFile", params={"file_id": file_id}
                )
                data = r.json() if r.status_code == 200 else {}
                fp = (data.get("result") or {}).get("file_path")
                if data.get("ok") and fp:
                    file_path = fp
                    token = t
                    break
            if not file_path:
                raise HTTPException(status_code=404, detail="Rasm topilmadi.")
            f = await client.get(f"{_TG_API}/file/bot{token}/{file_path}")
            if f.status_code != 200:
                raise HTTPException(status_code=404, detail="Rasm topilmadi.")
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001  (tarmoq/Telegram xatosi -> 404)
        raise HTTPException(status_code=404, detail="Rasm olinmadi.")

    media_type = "image/jpeg"
    if file_path.endswith(".png"):
        media_type = "image/png"
    elif file_path.endswith(".webp"):
        media_type = "image/webp"
    return Response(
        content=f.content,
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )

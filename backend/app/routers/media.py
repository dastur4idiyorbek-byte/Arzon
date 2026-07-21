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
from fastapi import APIRouter, HTTPException, Response

from ..config import settings

router = APIRouter(tags=["media"])

_TG_API = "https://api.telegram.org"


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

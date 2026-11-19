"""Upload and serve native-app media with private KYC access controls."""
from fastapi import APIRouter, Depends, File, Header, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Media, User
from ..security import get_current_user, is_super_admin

router = APIRouter(tags=["media"])
MAX_RASM_BAYT = 8 * 1024 * 1024


def get_optional_user(
    authorization: str = Header(default="", alias="Authorization"),
    db: Session = Depends(get_db),
) -> User | None:
    from ..services.auth import decode_token
    token = authorization[7:].strip() if authorization.lower().startswith("bearer ") else ""
    uid = decode_token(token) if token else None
    return db.get(User, uid) if uid is not None else None


@router.post("/api/media/upload")
async def media_upload(
    rasm: UploadFile = File(...),
    maxfiy: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw = await rasm.read()
    if not raw:
        raise HTTPException(400, "Rasm bo'sh.")
    if len(raw) > MAX_RASM_BAYT:
        raise HTTPException(413, "Rasm 8 MB dan oshmasin.")
    mime = (rasm.content_type or "image/jpeg").lower()
    if not mime.startswith("image/"):
        raise HTTPException(400, "Faqat rasm yuklash mumkin.")
    media = Media(mime=mime, data=raw, yuklagan_user_id=user.id, maxfiy=maxfiy)
    db.add(media)
    db.commit()
    db.refresh(media)
    return {"url": f"/media/db/{media.id}", "id": media.id}


@router.get("/media/db/{media_id}")
def media_db(
    media_id: int,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    media = db.get(Media, media_id)
    if media is None:
        raise HTTPException(404, "Rasm topilmadi.")
    if media.maxfiy and (
        user is None
        or (user.id != media.yuklagan_user_id and not is_super_admin(user))
    ):
        raise HTTPException(403, "Maxfiy rasmga ruxsat yo'q.")
    return Response(
        content=media.data,
        media_type=media.mime or "image/jpeg",
        headers={"Cache-Control": "private, no-store" if media.maxfiy else "public, max-age=86400"},
    )

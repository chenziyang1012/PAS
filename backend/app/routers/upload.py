import os
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.config import settings
from app.models import User
from app.auth import get_current_user
from app.schemas import Resp

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

@router.post("/image")
async def upload_image(file: UploadFile = File(...), _: User = Depends(get_current_user)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="只允许上传图片文件")
    today = datetime.now().strftime("%Y/%m")
    save_dir = os.path.join(settings.UPLOAD_DIR, today)
    os.makedirs(save_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(save_dir, filename)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    url = f"/uploads/{today}/{filename}"
    return Resp(data={"url": url})

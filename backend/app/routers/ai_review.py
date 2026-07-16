import base64
import os
import queue
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.config import settings
from app.database import SessionLocal, get_db
from app.models import Product, User
from app.schemas import Resp

router = APIRouter(tags=["ai_review"])

_queue: queue.Queue = queue.Queue()
_pending_ids: set[int] = set()
_lock = threading.Lock()


def enqueue_ai_review(product_id: int, prompt: str | None = None):
    custom_prompt = prompt or settings.DOUBAO_PROMPT
    with _lock:
        _pending_ids.add(product_id)
    _queue.put((product_id, custom_prompt))


def _do_ai_review(product_id: int, prompt: str):
    db = SessionLocal()
    try:
        product = db.get(Product, product_id)
        if not product:
            return

        api_key = settings.DOUBAO_API_KEY
        base_url = settings.DOUBAO_BASE_URL
        model = settings.DOUBAO_MODEL

        if not api_key or not model:
            return

        image_url = product.main_image
        if not image_url:
            product.ai_review_result = "无法审核：产品没有主图"
            product.ai_reviewed_at = datetime.now(timezone.utc)
            db.commit()
            return

        if image_url.startswith("/uploads/"):
            local_path = os.path.join(settings.UPLOAD_DIR, image_url[len("/uploads/"):])
            with open(local_path, "rb") as f:
                raw = f.read()
            b64 = base64.b64encode(raw).decode()
            ext = local_path.rsplit(".", 1)[-1].lower()
            mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(ext, "image/jpeg")
            img_content = {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        else:
            if image_url.startswith("//"):
                image_url = "https:" + image_url
            img_content = {"type": "image_url", "image_url": {"url": image_url}}

        text_content = {"type": "text", "text": f"产品名称：{product.product_name}\n\n{prompt}"}

        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=60)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": [img_content, text_content]}],
            max_tokens=1000,
        )
        result = response.choices[0].message.content or "（无输出）"

        product.ai_review_result = result
        product.ai_reviewed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        try:
            db.rollback()
            product = db.get(Product, product_id)
            if product:
                product.ai_review_result = f"AI审核失败：{str(e)[:500]}"
                product.ai_reviewed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _worker():
    while True:
        product_id, prompt = _queue.get()
        try:
            _do_ai_review(product_id, prompt)
        except Exception:
            pass
        finally:
            with _lock:
                _pending_ids.discard(product_id)
            _queue.task_done()


threading.Thread(target=_worker, daemon=True).start()

_settings_file = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".doubao_settings.json",
)


def _load_doubao_settings():
    if os.path.exists(_settings_file):
        import json
        with open(_settings_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        settings.DOUBAO_API_KEY = data.get("api_key", "")
        settings.DOUBAO_BASE_URL = data.get("base_url", settings.DOUBAO_BASE_URL)
        settings.DOUBAO_MODEL = data.get("model", "")
        settings.DOUBAO_PROMPT = data.get("prompt", "")


_load_doubao_settings()


@router.get("/api/settings/doubao")
def get_doubao_settings(current_user: User = Depends(require_roles("admin"))):
    return Resp(data={
        "base_url": settings.DOUBAO_BASE_URL,
        "model": settings.DOUBAO_MODEL,
        "prompt": settings.DOUBAO_PROMPT,
        "configured": bool(settings.DOUBAO_API_KEY and settings.DOUBAO_MODEL),
    })


@router.put("/api/settings/doubao")
def set_doubao_settings(body: dict = Body(...), current_user: User = Depends(require_roles("admin"))):
    import json
    data = {
        "api_key": body.get("api_key", ""),
        "base_url": body.get("base_url", settings.DOUBAO_BASE_URL),
        "model": body.get("model", ""),
        "prompt": body.get("prompt", ""),
    }
    with open(_settings_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    settings.DOUBAO_API_KEY = data["api_key"]
    settings.DOUBAO_BASE_URL = data["base_url"]
    settings.DOUBAO_MODEL = data["model"]
    settings.DOUBAO_PROMPT = data["prompt"]
    return Resp(message="配置已保存")


@router.post("/api/reviews/batch-ai-review")
def batch_ai_review(
    body: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("reviewer", "admin")),
):
    ids = body.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="请选择至少一个产品")
    if not settings.DOUBAO_API_KEY or not settings.DOUBAO_MODEL:
        raise HTTPException(status_code=400, detail="未配置豆包 API Key 或模型，请在系统设置中配置")
    if not settings.DOUBAO_PROMPT:
        raise HTTPException(status_code=400, detail="请先在系统设置中配置审核提示词")
    queued = 0
    for product_id in ids:
        if db.get(Product, product_id):
            enqueue_ai_review(product_id)
            queued += 1
    return Resp(data={"queued": queued})


@router.post("/api/reviews/{product_id}/ai-review")
def trigger_ai_review(
    product_id: int,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("reviewer", "admin")),
):
    if not settings.DOUBAO_API_KEY or not settings.DOUBAO_MODEL:
        raise HTTPException(status_code=400, detail="未配置豆包 API Key 或模型，请在系统设置中配置")
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    prompt = body.get("prompt") or settings.DOUBAO_PROMPT
    if not prompt:
        raise HTTPException(status_code=400, detail="请先在系统设置中配置审核提示词，或在此处输入提示词")
    enqueue_ai_review(product_id, prompt)
    return Resp(data={"queued": True})


@router.get("/api/reviews/{product_id}/ai-result")
def get_ai_result(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("reviewer", "admin")),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    with _lock:
        is_pending = product_id in _pending_ids
    return Resp(data={
        "ai_review_result": product.ai_review_result,
        "ai_reviewed_at": product.ai_reviewed_at.isoformat() if product.ai_reviewed_at else None,
        "is_pending": is_pending,
    })

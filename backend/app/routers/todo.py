"""待做列表 — 审核通过的产品自动出现；支持批量导入、素材爬取、生图、标记完成。"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Product, ProductMaterial, GeneratedImage, PromptTemplate
from app.schemas import Resp, BulkCreateRequest
from app.auth import get_current_user, require_roles
from app.scraper import scrape_product

router = APIRouter(prefix="/api/todo", tags=["todo"])


@router.get("")
def list_todo(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    creator_username: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == "reviewer":
        raise HTTPException(status_code=403, detail="无权访问")
    q = db.query(Product).filter(
        Product.status == "approved",
        Product.special_tag.is_(None),
        Product.is_completed == False,
    )
    # 选品员只看自己的
    if current_user.role == "selector":
        q = q.filter(Product.creator_id == current_user.id)
    if keyword:
        q = q.filter(Product.product_name.contains(keyword))
    if creator_username:
        q = q.join(User, Product.creator_id == User.id).filter(User.username.contains(creator_username))
    total = q.count()
    items = q.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Resp(data={
        "items": [_todo_item(p, db) for p in items],
        "total": total,
    })


def _todo_item(p: Product, db: Session) -> dict:
    gen_images = db.query(GeneratedImage).filter(GeneratedImage.product_id == p.id).all()
    no_logo = next((g for g in gen_images if not g.has_logo and g.status == "done"), None)
    with_logo = next((g for g in gen_images if g.has_logo and g.status == "done"), None)
    generating = any(g.status in ("pending", "generating") for g in gen_images)
    return {
        "id": p.id,
        "product_name": p.product_name,
        "product_link": p.product_link,
        "main_image": p.main_image,
        "manufacturer": p.manufacturer,
        "status": p.status,
        "creator": {"username": p.creator.username, "real_name": p.creator.real_name} if p.creator else None,
        "images": [{"id": img.id, "url": img.url} for img in p.images],
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "generated_images": {
            "no_logo": {"url": no_logo.url, "status": no_logo.status} if no_logo else None,
            "with_logo": {"url": with_logo.url, "status": with_logo.status} if with_logo else None,
            "generating": generating,
        },
    }


@router.post("/bulk")
def bulk_create_todo(
    body: BulkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("selector", "admin"):
        raise HTTPException(status_code=403, detail="无权创建产品")
    created = []
    for url in body.urls:
        url = url.strip()
        if not url:
            continue
        info = scrape_product(url, current_user.cookie_1688)
        product = Product(
            product_name=info.get("title") or url,
            product_link=url,
            main_image=info.get("image"),
            manufacturer=info.get("manufacturer"),
            status="approved",
            special_tag=None,
            is_completed=False,
            creator_id=current_user.id,
        )
        db.add(product)
        db.flush()
        created.append(product.id)
    db.commit()
    return Resp(data={"created": len(created), "ids": created})


@router.post("/{product_id}/complete")
def mark_complete(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("selector", "admin"):
        raise HTTPException(status_code=403, detail="无权操作")
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    if current_user.role != "admin" and product.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作")
    if product.status != "approved":
        raise HTTPException(status_code=400, detail="只有已通过审核的产品才能标记完成")
    product.is_completed = True
    product.special_tag = "done"
    db.commit()
    return Resp()


@router.post("/batch-complete")
def batch_complete(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("selector", "admin"):
        raise HTTPException(status_code=403, detail="无权操作")
    ids = body.get("ids", [])
    for pid in ids:
        product = db.get(Product, pid)
        if not product:
            continue
        if current_user.role != "admin" and product.creator_id != current_user.id:
            continue
        if product.status != "approved":
            continue
        product.is_completed = True
        product.special_tag = "done"
    db.commit()
    return Resp()


# ---- 素材管理 ----

@router.get("/{product_id}/materials")
def get_materials(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    materials = db.query(ProductMaterial).filter(ProductMaterial.product_id == product_id).order_by(ProductMaterial.sort_order).all()
    return Resp(data=[{"id": m.id, "type": m.type, "url": m.url, "sort_order": m.sort_order} for m in materials])


@router.post("/{product_id}/materials")
def add_material(product_id: int, body: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = ProductMaterial(
        product_id=product_id,
        type=body.get("type", "variant"),
        url=body["url"],
        sort_order=body.get("sort_order", 0),
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return Resp(data={"id": m.id, "type": m.type, "url": m.url})


@router.delete("/{product_id}/materials/{material_id}")
def delete_material(product_id: int, material_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    m = db.query(ProductMaterial).filter(ProductMaterial.id == material_id, ProductMaterial.product_id == product_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="素材不存在")
    db.delete(m)
    db.commit()
    return Resp()


@router.put("/{product_id}/materials/batch")
def batch_update_materials(product_id: int, body: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """批量更新素材分类 body: { items: [{id, type, sort_order}] }"""
    for item in body.get("items", []):
        m = db.query(ProductMaterial).filter(ProductMaterial.id == item["id"], ProductMaterial.product_id == product_id).first()
        if m:
            if "type" in item:
                m.type = item["type"]
            if "sort_order" in item:
                m.sort_order = item["sort_order"]
    db.commit()
    return Resp()


# ---- 素材爬取 ----

@router.post("/{product_id}/scrape-materials")
def scrape_materials(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """从产品的1688链接爬取所有图片作为素材"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    if not product.product_link or "1688.com" not in product.product_link:
        raise HTTPException(status_code=400, detail="该产品没有1688链接")

    from app.scraper import scrape_all_images
    images = scrape_all_images(product.product_link, current_user.cookie_1688)
    if "error" in images:
        raise HTTPException(status_code=400, detail=images["error"])

    # 清除旧素材
    db.query(ProductMaterial).filter(ProductMaterial.product_id == product_id).delete()

    # 保存新素材
    saved = []
    for i, url in enumerate(images.get("urls", [])):
        m = ProductMaterial(product_id=product_id, type="variant", url=url, sort_order=i)
        db.add(m)
        saved.append(url)
    db.commit()
    return Resp(data={"count": len(saved), "urls": saved})


# ---- 提示词模板 ----

@router.get("/templates")
def list_templates(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    templates = db.query(PromptTemplate).order_by(PromptTemplate.is_default.desc(), PromptTemplate.created_at.desc()).all()
    return Resp(data=[{
        "id": t.id, "name": t.name, "content": t.content,
        "is_default": t.is_default, "creator_id": t.creator_id,
    } for t in templates])


@router.post("/templates")
def create_template(body: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    t = PromptTemplate(
        name=body["name"],
        content=body["content"],
        is_default=body.get("is_default", False),
        creator_id=current_user.id,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return Resp(data={"id": t.id, "name": t.name})


@router.put("/templates/{template_id}")
def update_template(template_id: int, body: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    if "name" in body:
        t.name = body["name"]
    if "content" in body:
        t.content = body["content"]
    if "is_default" in body:
        t.is_default = body["is_default"]
    db.commit()
    return Resp()


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    t = db.get(PromptTemplate, template_id)
    if not t:
        raise HTTPException(status_code=404, detail="模板不存在")
    db.delete(t)
    db.commit()
    return Resp()


# ---- 生成图片 ----

@router.get("/{product_id}/generated")
def get_generated(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    images = db.query(GeneratedImage).filter(GeneratedImage.product_id == product_id).all()
    return Resp(data=[{
        "id": g.id, "has_logo": g.has_logo, "status": g.status,
        "url": g.url, "error": g.error,
    } for g in images])


@router.post("/{product_id}/generate")
def generate_images(product_id: int, body: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """触发生图 body: { template_id: int }"""
    from app.config import settings
    if not settings.OPENAI_API_KEY:
        raise HTTPException(status_code=400, detail="未配置 OpenAI API Key，请在系统设置中配置")

    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    materials = db.query(ProductMaterial).filter(ProductMaterial.product_id == product_id).order_by(ProductMaterial.sort_order).all()
    if not materials:
        raise HTTPException(status_code=400, detail="请先爬取并选择素材图片")

    # 获取提示词模板
    template_id = body.get("template_id")
    if template_id:
        template = db.get(PromptTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="提示词模板不存在")
        prompt_text = template.content
    else:
        raise HTTPException(status_code=400, detail="请选择提示词模板")

    # 清除旧的生成记录
    db.query(GeneratedImage).filter(GeneratedImage.product_id == product_id).delete()

    # 创建两条生成记录 (无logo + 有logo)
    gen_no_logo = GeneratedImage(product_id=product_id, has_logo=False, status="pending")
    gen_with_logo = GeneratedImage(product_id=product_id, has_logo=True, status="pending")
    db.add(gen_no_logo)
    db.add(gen_with_logo)
    db.commit()
    db.refresh(gen_no_logo)
    db.refresh(gen_with_logo)

    # 在后台线程中执行生图
    import threading
    threading.Thread(
        target=_do_generate,
        args=(product_id, gen_no_logo.id, gen_with_logo.id, prompt_text, [m.url for m in materials]),
        daemon=True,
    ).start()

    return Resp(data={"no_logo_id": gen_no_logo.id, "with_logo_id": gen_with_logo.id})


def _do_generate(product_id: int, no_logo_id: int, with_logo_id: int, prompt_text: str, material_urls: list[str]):
    """后台生图线程"""
    from app.database import SessionLocal
    from app.config import settings
    import os, requests as req

    db = SessionLocal()
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL)

        # 下载素材图片
        import tempfile
        temp_files = []
        for url in material_urls:
            try:
                if url.startswith("//"):
                    url = "https:" + url
                r = req.get(url, timeout=15)
                r.raise_for_status()
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp.write(r.content)
                tmp.close()
                temp_files.append(tmp.name)
            except Exception:
                continue

        if not temp_files:
            _update_gen_status(db, no_logo_id, "failed", error="无法下载素材图片")
            _update_gen_status(db, with_logo_id, "failed", error="无法下载素材图片")
            return

        out_dir = os.path.join(settings.UPLOAD_DIR, "generated", str(product_id))
        os.makedirs(out_dir, exist_ok=True)

        # 生成无logo版
        _update_gen_status(db, no_logo_id, "generating")
        try:
            result = client.images.edit(
                model="gpt-image-2",
                image=open(temp_files[0], "rb"),
                prompt=prompt_text,
                size="2048x2048",
                n=1,
            )
            # 保存结果
            img_data = result.data[0]
            if hasattr(img_data, 'b64_json') and img_data.b64_json:
                import base64
                img_bytes = base64.b64decode(img_data.b64_json)
            elif hasattr(img_data, 'url') and img_data.url:
                img_bytes = req.get(img_data.url, timeout=30).content
            else:
                raise Exception("API未返回图片数据")

            no_logo_path = os.path.join(out_dir, "no_logo.png")
            with open(no_logo_path, "wb") as f:
                f.write(img_bytes)

            # 用Pillow调整到2000x2000
            from PIL import Image
            img = Image.open(no_logo_path)
            img = img.resize((2000, 2000), Image.LANCZOS)
            img.save(no_logo_path)

            url_path = f"/uploads/generated/{product_id}/no_logo.png"
            _update_gen_status(db, no_logo_id, "done", url=url_path)

            # 更新产品主图
            product = db.get(Product, product_id)
            if product:
                product.main_image = url_path
                db.commit()
        except Exception as e:
            _update_gen_status(db, no_logo_id, "failed", error=str(e))

        # 生成有logo版
        _update_gen_status(db, with_logo_id, "generating")
        try:
            logo_prompt = prompt_text + "\n在主视觉区产品图的左上角放置 'logo' 文字，文字清晰可见。"
            result = client.images.edit(
                model="gpt-image-2",
                image=open(temp_files[0], "rb"),
                prompt=logo_prompt,
                size="2048x2048",
                n=1,
            )
            img_data = result.data[0]
            if hasattr(img_data, 'b64_json') and img_data.b64_json:
                import base64
                img_bytes = base64.b64decode(img_data.b64_json)
            elif hasattr(img_data, 'url') and img_data.url:
                img_bytes = req.get(img_data.url, timeout=30).content
            else:
                raise Exception("API未返回图片数据")

            with_logo_path = os.path.join(out_dir, "with_logo.png")
            with open(with_logo_path, "wb") as f:
                f.write(img_bytes)

            from PIL import Image
            img = Image.open(with_logo_path)
            img = img.resize((2000, 2000), Image.LANCZOS)
            img.save(with_logo_path)

            url_path = f"/uploads/generated/{product_id}/with_logo.png"
            _update_gen_status(db, with_logo_id, "done", url=url_path)
        except Exception as e:
            _update_gen_status(db, with_logo_id, "failed", error=str(e))

        # 清理临时文件
        for f in temp_files:
            try:
                os.unlink(f)
            except Exception:
                pass
    except Exception as e:
        _update_gen_status(db, no_logo_id, "failed", error=str(e))
        _update_gen_status(db, with_logo_id, "failed", error=str(e))
    finally:
        db.close()


def _update_gen_status(db: Session, gen_id: int, status: str, url: str | None = None, error: str | None = None):
    g = db.get(GeneratedImage, gen_id)
    if g:
        g.status = status
        if url:
            g.url = url
        if error:
            g.error = error
        db.commit()


# ---- OpenAI 配置 ----

@router.get("/settings/openai")
def get_openai_settings(current_user: User = Depends(require_roles("admin"))):
    from app.config import settings
    key = settings.OPENAI_API_KEY
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else key
    return Resp(data={
        "api_key": masked,
        "base_url": settings.OPENAI_BASE_URL,
        "configured": bool(key),
    })


@router.put("/settings/openai")
def set_openai_settings(body: dict, current_user: User = Depends(require_roles("admin"))):
    import os
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    lines = []
    found_key = False
    found_url = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    found_key = True
                    lines.append(f"OPENAI_API_KEY={body.get('api_key', '')}\n")
                elif line.startswith("OPENAI_BASE_URL="):
                    found_url = True
                    lines.append(f"OPENAI_BASE_URL={body.get('base_url', '')}\n")
                else:
                    lines.append(line)
    if not found_key:
        lines.append(f"OPENAI_API_KEY={body.get('api_key', '')}\n")
    if not found_url:
        lines.append(f"OPENAI_BASE_URL={body.get('base_url', '')}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    from app.config import settings
    settings.OPENAI_API_KEY = body.get("api_key", "")
    settings.OPENAI_BASE_URL = body.get("base_url", settings.OPENAI_BASE_URL)
    return Resp(message="配置已保存")

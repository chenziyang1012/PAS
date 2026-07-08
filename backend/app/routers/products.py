from datetime import datetime, timezone, date
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import User, Product, ProductImage
from app.schemas import (
    Resp, ProductCreate, ProductUpdate, ProductOut, ProductDetailOut,
    BulkCreateRequest, BulkDeleteRequest, BulkCompleteRequest, ScrapeRequest,
    CookieSettingRequest,
)
from app.auth import get_current_user, require_roles
from app.scraper import scrape_product

router = APIRouter(prefix="/api/products", tags=["products"])

def _check_product_access(product: Product, user: User):
    if user.role == "admin":
        return
    if user.role == "selector" and product.creator_id != user.id:
        raise HTTPException(status_code=403, detail="无权访问")
    if user.role == "reviewer" and product.status not in ("pending_review", "approved", "rejected"):
        raise HTTPException(status_code=403, detail="无权访问")

def _sync_images(db: Session, product: Product, urls: list[str]):
    db.query(ProductImage).filter(ProductImage.product_id == product.id).delete()
    for i, url in enumerate(urls):
        db.add(ProductImage(product_id=product.id, url=url, sort_order=i))

@router.get("")
def list_products(
    page: int = 1, page_size: int = 20,
    keyword: str | None = None,
    status: str | None = None,
    is_completed: bool | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Product).filter(Product.creator_id == current_user.id)
    if keyword:
        q = q.filter(Product.product_name.contains(keyword))
    if status:
        q = q.filter(Product.status == status)
    if is_completed is not None:
        q = q.filter(Product.is_completed == is_completed)
    if date_from:
        q = q.filter(func.date(Product.created_at) >= date_from)
    if date_to:
        q = q.filter(func.date(Product.created_at) <= date_to)
    total = q.count()
    items = q.order_by(Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Resp(data={"total": total, "items": [ProductOut.model_validate(p) for p in items]})

@router.get("/done")
def list_done(
    page: int = 1, page_size: int = 20,
    keyword: str | None = None,
    creator_username: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Product).filter(Product.special_tag == "done")
    if keyword:
        q = q.filter(Product.product_name.contains(keyword))
    if creator_username:
        q = q.join(User, Product.creator_id == User.id).filter(User.username.contains(creator_username))
    if date_from:
        q = q.filter(func.date(Product.updated_at) >= date_from)
    if date_to:
        q = q.filter(func.date(Product.updated_at) <= date_to)
    total = q.count()
    items = q.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Resp(data={"total": total, "items": [ProductOut.model_validate(p) for p in items]})

@router.get("/infringe")
def list_infringe(
    page: int = 1, page_size: int = 20,
    keyword: str | None = None,
    creator_username: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Product).filter(Product.special_tag == "infringe")
    if keyword:
        q = q.filter(Product.product_name.contains(keyword))
    if creator_username:
        q = q.join(User, Product.creator_id == User.id).filter(User.username.contains(creator_username))
    if date_from:
        q = q.filter(func.date(Product.updated_at) >= date_from)
    if date_to:
        q = q.filter(func.date(Product.updated_at) <= date_to)
    total = q.count()
    items = q.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Resp(data={"total": total, "items": [ProductOut.model_validate(p) for p in items]})

_ALLOWED_SCRAPE_HOSTS = {"1688.com", "www.1688.com", "detail.1688.com", "s.1688.com"}

def _validate_scrape_url(url: str) -> None:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(status_code=400, detail="URL 格式不合法")
        host = parsed.netloc.lower().split(":")[0]
        if host not in _ALLOWED_SCRAPE_HOSTS and not host.endswith(".1688.com"):
            raise HTTPException(status_code=400, detail="仅支持抓取 1688.com 域名的商品")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="URL 格式不合法")

@router.post("/scrape")
def scrape(body: ScrapeRequest, current_user: User = Depends(get_current_user)):
    _validate_scrape_url(body.url)
    result = scrape_product(body.url, current_user.cookie_1688)
    return Resp(data=result)

@router.post("/bulk")
def bulk_create(
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
            status="draft",
            special_tag=body.special_tag,
            creator_id=current_user.id,
        )
        db.add(product)
        db.flush()
        if info.get("image"):
            db.add(ProductImage(product_id=product.id, url=info["image"], sort_order=0))
        created.append(product.id)
    db.commit()
    return Resp(data={"created": len(created)})

@router.delete("/bulk")
def bulk_delete(
    body: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    products = db.query(Product).filter(Product.id.in_(body.ids)).all()
    for p in products:
        if p.creator_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail=f"无权删除产品 {p.id}")
    for p in products:
        db.delete(p)
    db.commit()
    return Resp(data={"deleted": len(products)})

@router.patch("/bulk-complete")
def bulk_complete(
    body: BulkCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("selector", "admin"):
        raise HTTPException(status_code=403, detail="无权操作")
    items = db.query(Product).filter(Product.id.in_(body.ids)).all()
    for p in items:
        if current_user.role != "admin" and p.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail=f"无权操作产品 {p.id}")
        if p.status != "approved":
            raise HTTPException(status_code=400, detail=f"产品 {p.product_name} 未通过审核，无法标记完成")
        p.is_completed = True
        p.special_tag = "done"
    db.commit()
    return Resp(data={"updated": len(items)})

@router.post("")
def create_product(body: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ("selector", "admin"):
        raise HTTPException(status_code=403, detail="无权创建产品")
    status = "pending_review" if body.action == "submit" else "draft"
    product = Product(
        product_name=body.product_name,
        product_link=body.product_link,
        main_image=body.main_image,
        manufacturer=body.manufacturer,
        category=body.category,
        description=body.description,
        status=status,
        creator_id=current_user.id,
        submit_time=datetime.now(timezone.utc) if body.action == "submit" else None,
    )
    db.add(product)
    db.flush()
    _sync_images(db, product, body.images)
    db.commit()
    db.refresh(product)
    return Resp(data=ProductOut.model_validate(product))

@router.post("/from-bookmarklet")
def from_bookmarklet(
    body: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("selector", "admin"):
        raise HTTPException(status_code=403, detail="无权创建产品")
    product = Product(
        product_name=body.product_name,
        product_link=body.product_link,
        main_image=body.main_image,
        manufacturer=body.manufacturer,
        status="draft",
        special_tag=body.category,
        creator_id=current_user.id,
    )
    db.add(product)
    db.flush()
    if body.main_image:
        db.add(ProductImage(product_id=product.id, url=body.main_image, sort_order=0))
    db.commit()
    db.refresh(product)
    return Resp(data=ProductOut.model_validate(product))

@router.get("/settings/cookie-1688")
def get_cookie_1688(current_user: User = Depends(require_roles("admin"))):
    from app.config import settings
    cookie = settings.COOKIE_1688
    return Resp(data={"cookie_1688": cookie[:20] + "..." if len(cookie) > 20 else cookie, "configured": bool(cookie)})


@router.put("/settings/cookie-1688")
def set_cookie_1688(body: CookieSettingRequest, current_user: User = Depends(require_roles("admin"))):
    import os
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("COOKIE_1688="):
                    found = True
                    lines.append(f"COOKIE_1688={body.cookie_1688}\n")
                else:
                    lines.append(line)
    if not found:
        lines.append(f"COOKIE_1688={body.cookie_1688}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    from app.config import settings
    settings.COOKIE_1688 = body.cookie_1688

    return Resp(message="Cookie 已保存")

@router.get("/my-cookie-1688")
def get_my_cookie(current_user: User = Depends(get_current_user)):
    cookie = current_user.cookie_1688 or ""
    return Resp(data={"configured": bool(cookie)})

@router.put("/my-cookie-1688")
def set_my_cookie(body: CookieSettingRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.cookie_1688 = body.cookie_1688
    db.commit()
    return Resp(message="Cookie 已保存")

@router.delete("/my-cookie-1688")
def delete_my_cookie(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.cookie_1688 = None
    db.commit()
    return Resp(message="Cookie 已删除")

@router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    _check_product_access(product, current_user)
    return Resp(data=ProductDetailOut.model_validate(product))

@router.put("/{product_id}")
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    if product.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权编辑")
    if product.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="当前状态不可编辑")
    for field in ("product_name", "product_link", "main_image", "manufacturer", "category", "description"):
        val = getattr(body, field)
        if val is not None:
            setattr(product, field, val)
    if body.images is not None:
        _sync_images(db, product, body.images)
    db.commit()
    db.refresh(product)
    return Resp(data=ProductOut.model_validate(product))

@router.patch("/{product_id}/complete")
def toggle_complete(
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
    return Resp(data={"is_completed": True})

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    if product.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除")
    if current_user.role != "admin" and product.status != "draft":
        raise HTTPException(status_code=400, detail="只能删除草稿状态产品")
    db.delete(product)
    db.commit()
    return Resp()

@router.post("/{product_id}/submit-review")
def submit_review(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    if product.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权提交")
    if product.status == "rejected":
        raise HTTPException(status_code=400, detail="已驳回的产品不能再次提交审核")
    if product.status != "draft":
        raise HTTPException(status_code=400, detail="当前状态不可提交")
    if not product.product_name:
        raise HTTPException(status_code=400, detail="产品名称必填")
    if not product.images and not product.main_image:
        raise HTTPException(status_code=400, detail="至少需要一张图片")
    product.status = "pending_review"
    product.submit_time = datetime.now(timezone.utc)
    db.commit()
    return Resp()

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Product, ProductImage
from app.schemas import Resp, ProductCreate, ProductUpdate, ProductOut, ProductDetailOut
from app.auth import get_current_user

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
    keyword: str | None = None, status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Product)
    if current_user.role == "selector":
        q = q.filter(Product.creator_id == current_user.id)
    if keyword:
        q = q.filter(Product.product_name.contains(keyword))
    if status:
        q = q.filter(Product.status == status)
    total = q.count()
    items = q.order_by(Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return Resp(data={"total": total, "items": [ProductOut.model_validate(p) for p in items]})

@router.post("")
def create_product(body: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in ("selector", "admin"):
        raise HTTPException(status_code=403, detail="无权创建产品")
    if body.action == "submit" and not body.images:
        raise HTTPException(status_code=400, detail="提交审核需至少一张图片")
    status = "pending_review" if body.action == "submit" else "draft"
    product = Product(
        product_name=body.product_name,
        product_link=body.product_link,
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
    if body.product_name is not None:
        product.product_name = body.product_name
    if body.product_link is not None:
        product.product_link = body.product_link
    if body.category is not None:
        product.category = body.category
    if body.description is not None:
        product.description = body.description
    if body.images is not None:
        _sync_images(db, product, body.images)
    db.commit()
    db.refresh(product)
    return Resp(data=ProductOut.model_validate(product))

@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    if product.creator_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="无权删除")
    if product.status != "draft":
        raise HTTPException(status_code=400, detail="只能删除草稿状态产品")
    db.delete(product)
    db.commit()
    return Resp()

@router.post("/{product_id}/submit-review")
def submit_review(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    if product.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权提交")
    if product.status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="当前状态不可提交")
    if not product.product_name:
        raise HTTPException(status_code=400, detail="产品名称必填")
    if not product.images:
        raise HTTPException(status_code=400, detail="至少需要一张图片")
    product.status = "pending_review"
    product.submit_time = datetime.now(timezone.utc)
    db.commit()
    return Resp()

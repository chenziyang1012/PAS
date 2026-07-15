from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Product, Review
from app.schemas import Resp, ReviewCreate, ProductDetailOut, ReviewOut
from app.auth import get_current_user, require_roles

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

@router.get("/pending")
def list_pending(
    page: int = 1, page_size: int = 20, keyword: str | None = None,
    creator_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("reviewer", "admin")),
):
    q = db.query(Product).filter(Product.status == "pending_review")
    if keyword:
        q = q.filter(Product.product_name.contains(keyword))
    if creator_id:
        q = q.filter(Product.creator_id == creator_id)
    total = q.count()
    items = q.order_by(Product.submit_time.asc(), Product.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
    from app.schemas import ProductOut
    return Resp(data={"total": total, "items": [ProductOut.model_validate(p) for p in items]})

@router.get("/{product_id}")
def review_detail(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("reviewer", "admin"))):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return Resp(data=ProductDetailOut.model_validate(product))

@router.post("/{product_id}/approve")
def approve(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("reviewer", "admin"))):
    product = db.query(Product).filter(Product.id == product_id).with_for_update().first()
    if not product or product.status != "pending_review":
        raise HTTPException(status_code=400, detail="产品不存在或状态不正确")
    product.status = "approved"
    db.add(Review(product_id=product.id, reviewer_id=current_user.id, result="approved"))
    db.commit()
    return Resp()

@router.post("/{product_id}/reject")
def reject(product_id: int, body: ReviewCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("reviewer", "admin"))):
    if not body.reject_type:
        raise HTTPException(status_code=400, detail="请选择驳回类型")
    if body.reject_type == "other" and not (body.reason or "").strip():
        raise HTTPException(status_code=400, detail="选择其他时驳回原因必填")
    product = db.query(Product).filter(Product.id == product_id).with_for_update().first()
    if not product or product.status != "pending_review":
        raise HTTPException(status_code=400, detail="产品不存在或状态不正确")
    product.status = "rejected"
    product.special_tag = body.reject_type
    db.add(Review(
        product_id=product.id,
        reviewer_id=current_user.id,
        result="rejected",
        reject_type=body.reject_type,
        reason=body.reason,
    ))
    db.commit()
    return Resp()

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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("reviewer", "admin")),
):
    q = db.query(Product).filter(Product.status == "pending_review")
    if keyword:
        q = q.filter(Product.product_name.contains(keyword))
    total = q.count()
    items = q.order_by(Product.submit_time.asc()).offset((page - 1) * page_size).limit(page_size).all()
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
    product = db.get(Product, product_id)
    if not product or product.status != "pending_review":
        raise HTTPException(status_code=400, detail="产品不存在或状态不正确")
    product.status = "approved"
    db.add(Review(product_id=product.id, reviewer_id=current_user.id, result="approved"))
    db.commit()
    return Resp()

@router.post("/{product_id}/reject")
def reject(product_id: int, body: ReviewCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("reviewer", "admin"))):
    if not body.reason:
        raise HTTPException(status_code=400, detail="驳回原因必填")
    product = db.get(Product, product_id)
    if not product or product.status != "pending_review":
        raise HTTPException(status_code=400, detail="产品不存在或状态不正确")
    product.status = "rejected"
    db.add(Review(product_id=product.id, reviewer_id=current_user.id, result="rejected", reason=body.reason))
    db.commit()
    return Resp()

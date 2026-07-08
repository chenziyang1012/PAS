from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import Resp, UserCreate, UserUpdate, UserStatusUpdate, ResetPasswordRequest, UserOut
from app.auth import get_current_user, hash_password, require_roles

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("")
def list_users(
    page: int = 1, page_size: int = 20,
    username: str | None = None, role: str | None = None, status: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    q = db.query(User)
    if username:
        q = q.filter(User.username.contains(username))
    if role:
        q = q.filter(User.role == role)
    if status:
        q = q.filter(User.status == status)
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return Resp(data={"total": total, "items": [UserOut.model_validate(u) for u in items]})

@router.post("")
def create_user(body: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if db.query(User).filter(User.username == body.username).first():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        real_name=body.real_name,
        role=body.role,
        status=body.status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return Resp(data=UserOut.model_validate(user))

@router.put("/{user_id}")
def update_user(user_id: int, body: UserUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    from fastapi import HTTPException
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.real_name is not None:
        user.real_name = body.real_name
    if body.role is not None:
        user.role = body.role
    if body.status is not None:
        user.status = body.status
    if body.password:
        user.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(user)
    return Resp(data=UserOut.model_validate(user))

@router.patch("/{user_id}/status")
def update_status(user_id: int, body: UserStatusUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    from fastapi import HTTPException
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = body.status
    db.commit()
    return Resp()

@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, body: ResetPasswordRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    from fastapi import HTTPException
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return Resp()

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    from fastapi import HTTPException
    from app.models import Product
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    if db.query(Product).filter(Product.creator_id == user_id).first():
        raise HTTPException(status_code=400, detail="该用户名下有商品，无法删除")
    db.delete(user)
    db.commit()
    return Resp()

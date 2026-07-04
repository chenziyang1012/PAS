from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, Resp, Token, UserOut
from app.auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if user.status == "disabled":
        raise HTTPException(status_code=403, detail="账号已禁用")
    token = create_access_token({"sub": str(user.id)})
    return Resp(data={"token": token, "user": UserOut.model_validate(user)})

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return Resp(data=UserOut.model_validate(current_user))

@router.post("/logout")
def logout():
    return Resp()

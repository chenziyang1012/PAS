from datetime import datetime
from pydantic import BaseModel

class Token(BaseModel):
    token: str
    user: "UserOut"

class LoginRequest(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}

class UserCreate(BaseModel):
    username: str
    password: str
    real_name: str
    role: str
    status: str = "enabled"

class UserUpdate(BaseModel):
    real_name: str | None = None
    role: str | None = None
    status: str | None = None
    password: str | None = None

class UserStatusUpdate(BaseModel):
    status: str

class ResetPasswordRequest(BaseModel):
    new_password: str

class ImageOut(BaseModel):
    id: int
    url: str
    sort_order: int
    model_config = {"from_attributes": True}

class ProductCreate(BaseModel):
    product_name: str
    product_link: str | None = None
    category: str | None = None
    description: str | None = None
    images: list[str] = []
    action: str = "draft"

class ProductUpdate(BaseModel):
    product_name: str | None = None
    product_link: str | None = None
    category: str | None = None
    description: str | None = None
    images: list[str] | None = None

class ProductOut(BaseModel):
    id: int
    product_name: str
    product_link: str | None
    category: str | None
    description: str | None
    status: str
    creator_id: int
    submit_time: datetime | None
    created_at: datetime
    updated_at: datetime
    images: list[ImageOut] = []
    creator: UserOut | None = None
    model_config = {"from_attributes": True}

class ReviewCreate(BaseModel):
    reason: str | None = None

class ReviewOut(BaseModel):
    id: int
    product_id: int
    reviewer_id: int
    result: str
    reason: str | None
    created_at: datetime
    reviewer: UserOut | None = None
    model_config = {"from_attributes": True}

class ProductDetailOut(ProductOut):
    reviews: list[ReviewOut] = []

class Resp(BaseModel):
    code: int = 0
    message: str = "ok"
    data: object = None

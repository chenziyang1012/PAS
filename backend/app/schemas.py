from datetime import datetime
from typing import Literal
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
    role: Literal["admin", "selector", "reviewer"]
    status: Literal["enabled", "disabled"] = "enabled"

class UserUpdate(BaseModel):
    real_name: str | None = None
    role: Literal["admin", "selector", "reviewer"] | None = None
    status: Literal["enabled", "disabled"] | None = None
    password: str | None = None

class UserStatusUpdate(BaseModel):
    status: Literal["enabled", "disabled"]

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
    main_image: str | None = None
    manufacturer: str | None = None
    category: str | None = None
    description: str | None = None
    images: list[str] = []
    action: str = "draft"

class ProductUpdate(BaseModel):
    product_name: str | None = None
    product_link: str | None = None
    main_image: str | None = None
    manufacturer: str | None = None
    category: str | None = None
    description: str | None = None
    images: list[str] | None = None

class BulkCreateRequest(BaseModel):
    urls: list[str]
    special_tag: str | None = None  # 'done' | 'infringe' | None

class BulkDeleteRequest(BaseModel):
    ids: list[int]

class BulkCompleteRequest(BaseModel):
    ids: list[int]

class ScrapeRequest(BaseModel):
    url: str

class ProductOut(BaseModel):
    id: int
    product_name: str
    product_link: str | None
    main_image: str | None
    manufacturer: str | None
    category: str | None
    description: str | None
    status: str
    is_completed: bool
    special_tag: str | None
    creator_id: int
    product_code: str | None = None
    done_at: datetime | None = None
    submit_time: datetime | None
    created_at: datetime
    updated_at: datetime
    images: list[ImageOut] = []
    creator: UserOut | None = None
    model_config = {"from_attributes": True}

class ReviewCreate(BaseModel):
    reject_type: Literal["infringe", "done", "other"] | None = None
    reason: str | None = None

class ReviewOut(BaseModel):
    id: int
    product_id: int
    reviewer_id: int
    result: str
    reject_type: str | None
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

class CookieSettingRequest(BaseModel):
    cookie_1688: str

class ProxySettingRequest(BaseModel):
    proxy_url: str

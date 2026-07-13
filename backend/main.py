import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import auth, users, products, reviews, upload, todo

Base.metadata.create_all(bind=engine)

def _migrate():
    """Add new columns to existing tables if they don't exist."""
    migrations = [
        ("products", "main_image", "VARCHAR(500)"),
        ("products", "manufacturer", "VARCHAR(100)"),
        ("products", "is_completed", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("products", "special_tag", "VARCHAR(20)"),
        ("products", "submit_time", "DATETIME"),
        ("reviews", "reject_type", "VARCHAR(20)"),
        ("users", "cookie_1688", "TEXT"),
    ]
    with engine.connect() as conn:
        for table, col, col_def in migrations:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                conn.commit()
            except Exception:
                pass  # column already exists

_migrate()

app = FastAPI(title="产品审核系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5176", "http://localhost:5177", "http://localhost:5178", "http://localhost:3000"],
    allow_origin_regex=r"https?://.*\.1688\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(reviews.router)
app.include_router(upload.router)
app.include_router(todo.router)

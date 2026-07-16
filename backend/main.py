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
        ("products", "approved_at", "DATETIME"),
        ("products", "product_code", "VARCHAR(100)"),
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

def _migrate_other_tag():
    """将历史驳回类型为 other 的产品补打 special_tag='other'。"""
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "UPDATE products SET special_tag='other' WHERE status='rejected' AND special_tag IS NULL"
            ))
            conn.commit()
        except Exception:
            pass

_migrate_other_tag()

def _backfill_approved_at():
    """已通过审核但 approved_at 为空的产品，用 updated_at 回填。"""
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "UPDATE products SET approved_at = updated_at WHERE status='approved' AND approved_at IS NULL"
            ))
            conn.commit()
        except Exception:
            pass

_backfill_approved_at()

def _cleanup_stale_pending():
    """Mark any pending/generating generated_images as failed on startup — they belong to threads that died with a previous process."""
    from app.database import SessionLocal
    from app.models import GeneratedImage
    db = SessionLocal()
    try:
        stale = db.query(GeneratedImage).filter(GeneratedImage.status.in_(["pending", "generating"])).all()
        for g in stale:
            g.status = "failed"
            g.error = "服务重启，请重新生图"
        if stale:
            db.commit()
    except Exception:
        pass
    finally:
        db.close()

_cleanup_stale_pending()

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

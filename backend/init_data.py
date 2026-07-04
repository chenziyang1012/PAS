"""Run once to create initial admin user: python init_data.py"""
from app.database import SessionLocal, engine
from app.models import Base, User
from app.auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    db.add(User(username="admin", password_hash=hash_password("admin123"), real_name="管理员", role="admin", status="enabled"))
    db.commit()
    print("Admin created: admin / admin123")
else:
    print("Admin already exists")
db.close()

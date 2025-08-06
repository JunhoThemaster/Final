# dependencies.py

# app/core/db.py 또는 app/dependencies.py 등
from sqlalchemy.orm import Session
from app.core.db import SessionLocal  # 세션 객체

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

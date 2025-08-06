# db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 실제 환경에 맞게 수정
DATABASE_URL = "mysql+pymysql://admin:1234@localhost:3306/siapp?charset=utf8mb4"


engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()



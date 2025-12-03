# create_tables.py

from app.core.db import engine, Base
from app.models import models  # models.py 내부 모든 모델 import

def create_all_tables():
    print("테이블 생성 중...")
    Base.metadata.create_all(bind=engine)
    print("모든 테이블이 생성되었습니다.")

if __name__ == "__main__":
    create_all_tables()

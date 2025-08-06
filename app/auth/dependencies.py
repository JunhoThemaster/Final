# app/auth/dependencies.py

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from app.auth.jwt_handler import decode_jwt_token  # JWT 디코더
# from app.models.user import User  # 실제 유저 모델

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/user/login")

# 실제로는 User가 아니라 Dict일 수도 있음 → 타입을 유연하게
async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_jwt_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    return payload  # 보통 {"sub": "user_id"} 같은 딕트 형태

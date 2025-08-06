from fastapi import APIRouter, Depends,HTTPException
from pydantic import BaseModel
import jwt
import datetime
from ....services.JwtUitls import token_utils
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel
from ....services.audio_module import save_and_transcribe,predict_service
from ....services.websocket import manager as ms
import numpy as np
from scipy.signal import resample_poly
from fastapi import APIRouter, Query
import openai
import librosa
from app.services.auth_service import hash_password
from ....services.interview_generator import InterviewGenerator
from ....auth.jwt_handler import create_access_token,decode_jwt_token
from ....auth.dependencies import get_current_user
from app.models.models import User
from sqlalchemy.orm import Session
import uuid
from app.dependencies import get_db
from passlib.context import CryptContext



def convert_pcm16_bytes_to_float32_array(pcm_bytes: bytes) -> np.ndarray:
    int16_array = np.frombuffer(pcm_bytes, dtype=np.int16)
    float_array = int16_array.astype(np.float32) / 32768.0  # normalize to [-1, 1]
    return float_array
def downsample_to_16k(audio: np.ndarray, orig_sr: int) -> np.ndarray:
    if orig_sr == 16000:
        return audio
    # up/down 비율 계산
    gcd = np.gcd(orig_sr, 16000)
    up = 16000 // gcd
    down = orig_sr // gcd
    return resample_poly(audio, up, down)

import wave
def save_pcm_as_wav(pcm_bytes: bytes, wav_path: str, sample_rate=16000):
    audio_data = np.frombuffer(pcm_bytes, dtype=np.int16)

    with wave.open(wav_path, 'wb') as wf:
        wf.setnchannels(1)          # Mono
        wf.setsampwidth(2)          # 16bit PCM = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data.tobytes())

        
router = APIRouter(
    prefix="/api/user",  # 이 경로가 모든 API 앞에 붙음
    tags=["user"]        # Swagger에서 보여질 카테고리 이름
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginData(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(data: LoginData, db: Session = Depends(get_db)):
    # ✅ 1. 이메일로 유저 조회
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="존재하지 않는 사용자입니다.")

    # ✅ 2. 비밀번호 검증
    if not pwd_context.verify(data.password, user.password):
        raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다.")

    # ✅ 3. 토큰 생성
    token = create_access_token(data={"sub": user.name})
    return {"access_token": token, "token_type": "bearer"}



from pydantic import BaseModel

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str
RegisterRequest.model_rebuild()

@router.post("/Register")
def register_user(request: RegisterRequest,db: Session = Depends(get_db) ):
    # 이메일 중복 체크
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

    # 사용자 생성
    new_user = User(
        id=str(uuid.uuid4()),
        name=request.username,
        email=request.email,
        password=hash_password(request.password)
    )
    db.add(new_user)
    db.commit()

    return {"message": "회원가입 성공"}




import tempfile
from fastapi import APIRouter, UploadFile, File, WebSocket, HTTPException, Query


from ....services.audio_module.clova_stt import clova_transcribe
from ....services.audio_module.audio_io import load_audio_float32
from ....services.audio_module.audio_convert import convert_webm_to_wav
from ....services.audio_module import predict_service
import tempfile, os
from fastapi import UploadFile, File, Query, HTTPException

from fastapi import Request

import json
from datetime import datetime

SAVE_DIR = "./saved_audios"  # 원하는 저장 경로
from app.models.models import InterviewAudioAnalyze
from fastapi import UploadFile, File, Query, HTTPException
from fastapi import UploadFile, File, Form

@router.post("/audio/{user_id}")
async def audio_analyze(
    user_id: str,         # 🔥 인터뷰 ID 추가
    question: str = Form(...),             # 🔥 질문 내용
    token: str = Query(...),
    interview_id: str = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db),         # 🔥 DB 세션 주입
):
    # 1️⃣ 토큰 검증
    if not token_utils.verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 2️⃣ 저장 경로 준비
    print(user_id)
    user_dir = os.path.join(SAVE_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    user = db.query(User).filter(User.name == user_id).first()

    print(user_id)
    # 3️⃣ 오디오 저장
    raw = await audio_file.read()
    content_type = audio_file.content_type or ""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        if content_type == "audio/wav":
            tmp.write(raw)
        else:
            tmp.close()
            save_pcm_as_wav(raw, tmp_path, sample_rate=16000)

    try:
        # 4️⃣ 분석
        text = clova_transcribe(tmp_path)
        y = load_audio_float32(tmp_path)
        emotion, probs = predict_service.predict_emotion(y)
    finally:
        os.remove(tmp_path)

    # 5️⃣ 확률 맵
    label_classes = np.load("app/services/audio_module/label_encoder_classes.npy", allow_pickle=True)
    probs_map = {cls: float(p) for cls, p in zip(label_classes, probs)}
    # 6️⃣ DB 저장
    analysis = InterviewAudioAnalyze(
        interview_id=interview_id,
        user_id=user.id,
        timestamp=datetime.utcnow(),
        question=question,
        answer=text.strip(),
        emotion=emotion,
        probabilities=probs_map
    )
    db.add(analysis)
    db.commit()

    # 7️⃣ 파일도 백업용 저장 (선택)
    result = {
        "user_id": user.id,
        "interview_id": interview_id,
        "timestamp": timestamp,
        "question": question,
        "text": text.strip(),
        "emotion": emotion,
        "probabilities": probs_map,
    }
    json_path = os.path.join(user_dir, f"{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 결과 저장 완료: {json_path}")
    return result

class FieldRequest(BaseModel):
    field: str


interview_generator = InterviewGenerator()



from pydantic import BaseModel
from app.models.models import Interview
from uuid import uuid4

class InterviewSetupRequest(BaseModel):
    jobUrl: str

@router.post("/interview/setup/{cate}/{n_q}")
async def setup_interview(
    cate: str,
    n_q: int,
    req: InterviewSetupRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),  # 🔑 DB 세션 추가
):
    

    """면접 세션 설정"""
    try:
       
        job_url = req.jobUrl
        interview_id = str(uuid4())  # 🔐 인터뷰 UUID 생성

        print(f"🎯 jobUrl 수신됨: {job_url}")

        # 🔹 1. 질문 생성
        questions = await interview_generator.generate_questions(
            cate,
            job_url,
            n_q
        )
        user = db.query(User).filter(User.name == user['sub']).first()
        # 🔹 2. 인터뷰 객체 생성 및 저장
        new_interview = Interview(
            id=interview_id,
            user_id=user.id,
            job_position=cate,
            job_url=job_url
        )
        db.add(new_interview)
        db.commit()
        
        return {
            "interview_id" : new_interview.id,
            "user_id": user.id,
            "questions": questions,
            "job_position": cate,
            "job_url": job_url,
            
            "message": "면접 세션이 생성되었습니다."
        }

    except Exception as e:
        print(f"❌ 면접 설정 오류: {e}")
        raise HTTPException(status_code=500, detail=f"면접 설정 오류: {str(e)}")



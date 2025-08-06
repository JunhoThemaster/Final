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
from ....services.interview_generator import InterviewGenerator
from ....auth.jwt_handler import create_access_token
from ....auth.dependencies import get_current_user

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

FAKE_USERNAME = "admin"
FAKE_PASSWORD = "1234"




class LoginData(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(data: LoginData):
    # 🔐 여기서 실제 유저 인증 로직 (DB 조회 등)을 넣을 수 있음
    if data.username == "admin" and data.password == "1234":
        # ✅ JWT 생성 함수 사용
        token = create_access_token(data={"sub": data.username})
        return {"access_token": token, "token_type": "bearer"}
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


## 오디오 송신 웹소켓 엔드포인트


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

from fastapi import UploadFile, File, Query, HTTPException
from fastapi import UploadFile, File, Form

@router.post("/audio/{user_id}")
async def audio_analyze(
    user_id: str,
    token: str = Query(...),
    audio_file: UploadFile = File(...),
    question:str = Form(...)
):
    # 1️⃣ 토큰 검증
    if not token_utils.verify_token(token):
        raise HTTPException(status_code=401, detail="Unauthorized")

    # 2️⃣ 결과(JSON) 저장 폴더 및 타임스탬프 준비
    user_dir = os.path.join(SAVE_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # 3️⃣ 바이트 읽기
    raw = await audio_file.read()
    content_type = audio_file.content_type or ""
    print(f"📨 질문 수신됨: {question}")
    # 4️⃣ 임시 WAV 파일 생성
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        if content_type == "audio/wav":
            tmp.write(raw)  # 이미 WAV 헤더 포함된 경우
        else:
            # PCM16 바이트 → WAV 변환
            tmp.close()  # save_pcm_as_wav가 같은 경로에 쓸 수 있도록
            save_pcm_as_wav(raw, tmp_path, sample_rate=16000)

    try:
        # 5️⃣ Clova STT + 감정 예측
        text = clova_transcribe(tmp_path)
        y = load_audio_float32(tmp_path)
        emotion, probs = predict_service.predict_emotion(y)
    finally:
        # 6️⃣ 임시 WAV 파일 삭제
        os.remove(tmp_path)

    # 7️⃣ 확률 맵 생성
    label_classes = np.load(
        "app/services/audio_module/label_encoder_classes.npy",
        allow_pickle=True
    )
    probs_map = {cls: float(p) for cls, p in zip(label_classes, probs)}

    # 8️⃣ JSON 결과 저장
    result = {
        "user_id":     user_id,
        "timestamp":   timestamp,
        "text":        text.strip(),
        "emotion":     emotion,
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
@router.get("/questions/categories")
async def get_job_categories():
    
    """직무 카테고리 반환"""
    try:
        categories = interview_generator.get_available_positions()
        return {"categories": categories}
    except Exception as e:
        print(f"❌ 카테고리 조회 오류: {e}")
        return {"categories": ["Management", "Sales Marketing", "ICT", "Design"]}




from pydantic import BaseModel

from pydantic import BaseModel

class InterviewSetupRequest(BaseModel):
    jobUrl: str

@router.post("/interview/setup/{cate}/{n_q}")
async def setup_interview(
    cate: str,
    n_q: int,
    req: InterviewSetupRequest,
    user=Depends(get_current_user)
):
    """면접 세션 설정"""
    try:
        user_id = user["sub"]
        job_url = req.jobUrl

        print(f"🎯 jobUrl 수신됨: {job_url}")

        # ✅ 수정: 3개 인자 전달
        questions = await interview_generator.generate_questions(
            cate,
            job_url,
            n_q
        )

        return {
            "user_id": user_id,
            "questions": questions,
            "job_position": cate,
            "job_url": job_url,
            "message": "면접 세션이 생성되었습니다."
        }

    except Exception as e:
        print(f"❌ 면접 설정 오류: {e}")
        raise HTTPException(status_code=500, detail=f"면접 설정 오류: {str(e)}")




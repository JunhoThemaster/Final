from fastapi import APIRouter, WebSocket, Depends, HTTPException
from app.DL_model.MLP import analyze_vector, emotion_to_onehot
from PIL import Image
import io
import json
import base64
import numpy as np
from deepface import DeepFace
from app.models.models import Interview, InterviewVideoAnalyze
from app.dependencies import get_db
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timedelta  # ⏰ 저장 주기 조절용

router = APIRouter()

@router.websocket("/ws/video")
async def analyze_ws(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    print("🟢 WebSocket 클라이언트 연결됨")

    total_blinks = 0
    last_saved_time = datetime.utcnow() - timedelta(seconds=3)  # 초기값은 3초 전으로 설정

    while True:
        try:
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)

            interview_id = data.get("interviewid")
            interview_obj = db.query(Interview).filter(Interview.id == interview_id).first()

            image_data = base64.b64decode(data.get("image", ""))
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            np_img = np.array(image)

            try:
                result = DeepFace.analyze(np_img, actions=["emotion"], enforce_detection=False)[0]
                emotion = result["dominant_emotion"]
                confidence = result["emotion"][emotion] / 100
            except Exception as e:
                print("❌ DeepFace 분석 실패:", str(e))
                await websocket.send_json({"error": "emotion_analysis_failed"})
                continue

            gaze_x = data.get("gaze_x", 0.0)
            gaze_y = data.get("gaze_y", 0.0)
            ear = data.get("ear", 0.0)
            blink_count = data.get("blink_count", 0)
            head_pose = data.get("head_pose", [0.0, 0.0, 0.0])
            posture = data.get("posture", 0)

            vector = (
                emotion_to_onehot(emotion) +
                [confidence, gaze_x, gaze_y, ear, blink_count] +
                head_pose
            )

            prediction = analyze_vector(vector)

            blink_delta = blink_count
            total_blinks += blink_delta

            response = {
                "emotion": prediction,
                "raw_emotion": emotion,
                "confidence": float(np.round(confidence, 3)),
                "blink_count": int(blink_delta),
                "total_blink_count": int(total_blinks),
                "posture": str(posture),
            }

            # 🔽 3초마다만 저장
            now = datetime.utcnow()
            if now - last_saved_time >= timedelta(seconds=3):
                analysis = InterviewVideoAnalyze(
                    interview_id=interview_id,
                    timestamp=now,
                    emotion=prediction,
                    raw_emotion=emotion,
                    confidence=confidence,
                    blink_count=blink_count,
                    posture=str(posture),
                    gaze_x=gaze_x,
                    gaze_y=gaze_y,
                    head_pose=head_pose,
                    ear=ear
                )
                db.add(analysis)
                db.commit()
                last_saved_time = now
                print("✅ 3초 주기로 감정 분석 결과 저장됨")

            await websocket.send_json(response)

        except Exception as e:
            print("❌ WebSocket 처리 중 오류:", str(e))
            break

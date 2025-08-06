from fastapi import APIRouter, WebSocket
from app.DL_model.MLP import analyze_vector, emotion_to_onehot
from PIL import Image
import io
import json
import base64
import numpy as np
from deepface import DeepFace

router = APIRouter()

@router.websocket("/ws/video")
async def analyze_ws(websocket: WebSocket):
    await websocket.accept()
    print("🟢 WebSocket 클라이언트 연결됨")

    total_blinks = 0  # ✅ 전체 누적 깜빡임 수

    while True:
        try:
            # print("📥 메시지 수신 대기 중...")
            data_raw = await websocket.receive_text()
            data = json.loads(data_raw)
            # print("📩 수신된 JSON keys:", list(data.keys()))

            # ✅ 이미지 디코딩
            image_data = base64.b64decode(data.get("image", ""))
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            np_img = np.array(image)


            # ✅ DeepFace 감정 분석
            try:
                result = DeepFace.analyze(np_img, actions=["emotion"], enforce_detection=False)[0]
                emotion = result["dominant_emotion"]
                confidence = result["emotion"][emotion] / 100
                # print(f"🧠 감정 분석: {emotion} ({confidence:.2f})")
            except Exception as e:
                print("❌ DeepFace 분석 실패:", str(e))
                await websocket.send_json({"error": "emotion_analysis_failed"})
                continue

            # ✅ 방어 처리된 입력값 추출
            gaze_x = data.get("gaze_x", 0.0)
            gaze_y = data.get("gaze_y", 0.0)
            ear = data.get("ear", 0.0)  # ← 에러 방지 핵심
            blink_count = data.get("blink_count", 0)
            head_pose = data.get("head_pose", [0.0, 0.0, 0.0])
            posture = data.get("posture", 0)

            # print(f"👁️ EAR: {ear} | 👀 Gaze: ({gaze_x}, {gaze_y}) | 🧠 Head Pose: {head_pose}")

            # ✅ MLP 입력 벡터 구성
            vector = (
                emotion_to_onehot(emotion) +
                [confidence, gaze_x, gaze_y, ear, blink_count] +
                head_pose
            )

            prediction = analyze_vector(vector)
            # print("✅ 감정 예측 결과:", prediction)

            # ✅ 깜빡임 누적 계산
            blink_delta = blink_count
            total_blinks += blink_delta
            # print(f"👁️ 이번 깜빡임 수: {blink_delta}, 누적: {total_blinks}")

            # ✅ 응답 구성
            response = {
                "emotion": prediction,
                "raw_emotion": emotion,
                "confidence": float(np.round(confidence, 3)),  # 👈 float32 → float 변환
                "blink_count": int(blink_delta),
                "total_blink_count": int(total_blinks),
                "posture": str(posture),  # 혹시 posture가 np.str_이면 str 변환 필요
            }


            await websocket.send_json(response)
            # print("📤 응답 전송 완료:", response)

        except Exception as e:
            print("❌ WebSocket 처리 중 오류:", str(e))
            break
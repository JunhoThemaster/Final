import React, { useEffect, useRef, useState } from "react";
import { FaceMesh } from "@mediapipe/face_mesh";
import { Pose } from "@mediapipe/pose";
import { Camera } from "@mediapipe/camera_utils";
import {
  drawCustomFaceMesh,
  drawPoseSkeleton,
} from "../utils/drawingUtils";

interface PoseTrackerProps {
  interviewid :string;
  onCameraReady: () => void;
}

const PoseTracker: React.FC<PoseTrackerProps> = ({ onCameraReady,interviewid }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cameraRef = useRef<Camera | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const hasStartedRef = useRef(false);

  const [blinkCount, setBlinkCount] = useState(0);
  const blinkCountRef = useRef(0);
  const [analysisResult, setAnalysisResult] = useState("분석 대기 중");
  const postureRef = useRef("정상");
  const [postureState, setPostureState] = useState("정상");
  const unstableSideRef = useRef<"left" | "right" | null>(null); // ✅ 즉시 렌더링을 위한 ref
  const earRef = useRef(0);

  const faceResultsRef = useRef<any>(null);
  const poseResultsRef = useRef<any>(null);
  const wasEyeClosedRef = useRef(false);

  const EAR_THRESHOLD = 0.21;

  const calculateEAR = (landmarks: any): number => {
    const left = [33, 160, 158, 133, 153, 144];
    const right = [362, 385, 387, 263, 373, 380];
    const dist = (a: any, b: any) => Math.hypot(a.x - b.x, a.y - b.y);
    const avgEAR = (eye: number[]) => {
      const lm = eye.map((i) => landmarks[i]);
      return ((dist(lm[1], lm[5]) + dist(lm[2], lm[4])) / (2 * dist(lm[0], lm[3])));
    };
    return (avgEAR(left) + avgEAR(right)) / 2;
  };

  const processBlink = (ear: number) => {
    if (ear < EAR_THRESHOLD && !wasEyeClosedRef.current) {
      blinkCountRef.current += 1;
      setBlinkCount((prev) => prev + 1);
      wasEyeClosedRef.current = true;
      console.log("👁️ 눈 깜빡임 감지");
    } else if (ear >= EAR_THRESHOLD) {
      wasEyeClosedRef.current = false;
    }
  };

  const judgePostureFromPose = (poseLandmarks: any) => {
    if (!poseLandmarks) return;

    const left = poseLandmarks[11];
    const right = poseLandmarks[12];
    const dy = left.y - right.y;
    const threshold = 0.06;

    if (Math.abs(dy) > threshold) {
      const direction: "left" | "right" = dy > 0 ? "left" : "right";
      postureRef.current = "불안정";
      setPostureState("불안정");
      unstableSideRef.current = direction; // ✅ 방향 즉시 저장
      console.log("📏 자세 상태: 불안정 | ↔ 방향:", direction);
    } else {
      postureRef.current = "정상";
      setPostureState("정상");
      unstableSideRef.current = null;
      console.log("📏 자세 상태: 정상");
    }
  };

  const sendFeaturesWithImage = () => {
    const video = videoRef.current;
    if (!video || socketRef.current?.readyState !== WebSocket.OPEN) return;

    const faceLandmarks = faceResultsRef.current?.multiFaceLandmarks?.[0];
    const poseLandmarks = poseResultsRef.current?.poseLandmarks;

    if (!faceLandmarks) {
      console.warn("⚠️ 얼굴 랜드마크 없음");
      return;
    }

    const irisX = (faceLandmarks[468]?.x + faceLandmarks[473]?.x) / 2 || 0;
    const irisY = (faceLandmarks[468]?.y + faceLandmarks[473]?.y) / 2 || 0;
    const nose = faceLandmarks[1];
    const headPose = nose ? [nose.x, nose.y, nose.z] : [0, 0, 0];

    if (poseLandmarks) {
      judgePostureFromPose(poseLandmarks);
    }

    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const base64 = canvas.toDataURL("image/jpeg").split(",")[1];

    const payload = {
      timestamp: new Date().toISOString(),
      interviewid : interviewid,
      blink_count: blinkCountRef.current,
      gaze_x: irisX,
      gaze_y: irisY,
      head_pose: headPose,
      posture: postureRef.current,
      image: base64,
      ear: earRef.current,
    };

    socketRef.current.send(JSON.stringify(payload));
    console.log("📤 서버 전송:", payload);

    blinkCountRef.current = 0;
    setBlinkCount(0);
  };

  const drawAll = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!ctx || !canvas) return;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);

    const video = videoRef.current;
    if (video) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    }

    if (faceResultsRef.current?.multiFaceLandmarks) {
      for (const landmarks of faceResultsRef.current.multiFaceLandmarks) {
        drawCustomFaceMesh(ctx, landmarks);
      }
    }

    if (poseResultsRef.current?.poseLandmarks) {
      drawPoseSkeleton(ctx, poseResultsRef.current.poseLandmarks);
    }

    ctx.restore();
  };

  useEffect(() => {
    if (hasStartedRef.current) return;
    hasStartedRef.current = true;

    const videoElement = videoRef.current!;
    let faceMesh: FaceMesh;
    let pose: Pose;

    const initMediaPipe = () => {
      faceMesh = new FaceMesh({
        locateFile: (file) =>
          `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
      });
      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });
      faceMesh.onResults((results) => {
        faceResultsRef.current = results;
        const landmarks = results?.multiFaceLandmarks?.[0];
        if (landmarks) {
          const ear = calculateEAR(landmarks);
          earRef.current = ear;
          processBlink(ear);
          //console.log("👁️ EAR:", ear.toFixed(3));
        }
        drawAll();
      });

      pose = new Pose({
        locateFile: (file) =>
          `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
      });
      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });
      pose.onResults((results) => {
        poseResultsRef.current = results;
        drawAll();
      });
    };

    const initWebSocket = () => {
      socketRef.current = new WebSocket("ws://localhost:8000/ws/video");

      socketRef.current.onopen = () => {
        console.log("✅ WebSocket 연결됨");
        setInterval(() => {
          sendFeaturesWithImage();
        }, 1000);
      };

      socketRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("📨 감정 결과:", data.emotion);
          console.log("👁️ 눈 깜빡임 수:", data.blink_count);
          console.log("📐 자세 상태:", data.posture);
          setAnalysisResult(data.emotion);
        } catch (err) {
          console.warn("⚠️ WebSocket 응답 파싱 실패:", err);
        }
      };

      socketRef.current.onerror = (err) => {
        console.error("❌ WebSocket 에러:", err);
      };
    };

    const startCamera = () => {
      cameraRef.current = new Camera(videoElement, {
        onFrame: async () => {
          await faceMesh.send({ image: videoElement });
          await pose.send({ image: videoElement });
        },
        width: 640,
        height: 480,
      });
      cameraRef.current.start().then(() => {
        console.log("📸 카메라 시작됨");
      });
    };

    videoElement.onloadeddata = () => {
      console.log("🎥 카메라 재생됨 → WebSocket 시작");
      onCameraReady();
      initWebSocket();
    };

    initMediaPipe();
    startCamera();

    return () => {
      cameraRef.current?.stop();
      socketRef.current?.close();
    };
  }, [onCameraReady]);

  return (
    <div className="camera-container">
      <video
        ref={videoRef}
        className="video-feed"
        playsInline
        muted
        autoPlay
        width={640}
        height={480}
        style={{ position: "absolute", left: 0, top: 0, zIndex: 0 }}
      />
      <canvas
        ref={canvasRef}
        className="canvas-overlay"
        width={640}
        height={480}
      />

      {/* ✅ 방향 따라 반짝이 UI 조건부 표시 */}
     {postureState === "불안정" && (
  <div className="blinker-warning">
    <div className="blinker-slot">
      {unstableSideRef.current === "left" && <div className="blinker left" />}
    </div>
    <p className="warning-text">자세가 불안정합니다!</p>
    <div className="blinker-slot">
      {unstableSideRef.current === "right" && <div className="blinker right" />}
    </div>
  </div>
)}

      <p style={{ marginTop: "500px", fontSize: "18px", fontWeight: "bold" }}>
        현재 감정 상태: {analysisResult}
      </p>
    </div>
  );
};

export default PoseTracker;
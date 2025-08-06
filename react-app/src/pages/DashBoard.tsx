import React, { useState } from "react";
import PoseTracker from "../components/PoseTracker";
// ✅ 이렇게 되어야 함
import VoiceLevelMeter from "../components/VoiceLevelMeter";

import "../dashboard.css";
import { parse } from "path";

function getUserIdFromToken(token: string): string | null {
  try {
    const payload = token.split(".")[1];         // JWT의 payload 부분
    const decoded = atob(payload);               // base64 디코딩
    const parsed = JSON.parse(decoded);
    console.log(parsed.sub)          // JSON 파싱
    return parsed.sub || null;                   // "sub"에서 user_id 추출
  } catch (err) {
    console.error("❌ 토큰 파싱 실패:", err);
    return null;
  }
}




const DashBoard: React.FC = () => {
  const [cameraOn, setCameraOn] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleCameraReady = () => {
    console.log("🎥 카메라 준비 완료 → 로딩 종료");
    setLoading(false);
  };

  const handleCameraToggle = () => {
    if (!cameraOn) {
      setCameraOn(true);
      setLoading(true);
      console.log("🎬 카메라 열기 시도");
    } else {
      setCameraOn(false);
      console.log("🛑 카메라 종료");
    }
  };

  const token = localStorage.getItem("token") ?? "";
  var UserId = null;
  if (token){
      UserId = getUserIdFromToken(token);
  }
  

  return (
    <div className="dashboard">
      <h1>감정 및 자세 분석 대시보드</h1>

      <button className="camera-toggle-button" onClick={handleCameraToggle}>
        {cameraOn ? "카메라 끄기" : "카메라 열기"}
      </button>

      {loading && (
        <div className="loading">
          <div className="loader"></div>
          <p>카메라 준비 중...</p>
        </div>
      )}

  
    </div>
  );
};

export default DashBoard;

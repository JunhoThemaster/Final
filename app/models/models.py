# app/models/models.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.mysql import JSON as MySQLJSON
from datetime import datetime
from app.core.db import Base


# 🔹 1. User 테이블
class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(200), nullable=False)  
    interviews = relationship("Interview", back_populates="user")
    audio_analyses = relationship("InterviewAudioAnalyze", back_populates="user")


# 🔹 2. Interview (면접 세션) 테이블
class Interview(Base):
    __tablename__ = "interviews"

    id = Column(String(50), primary_key=True, index=True)  # 예: UUID 사용 가능
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    job_position = Column(String(100), nullable=False)
    job_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interviews")
    audio_analyses = relationship("InterviewAudioAnalyze", back_populates="interview")


# 🔹 3. InterviewAudioAnalyze 테이블
class InterviewAudioAnalyze(Base):
    __tablename__ = "interview_audio_analyze"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(String(50), ForeignKey("interviews.id"), nullable=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    emotion = Column(String(50), nullable=False)
    probabilities = Column(MySQLJSON, nullable=False)

    user = relationship("User", back_populates="audio_analyses")
    interview = relationship("Interview", back_populates="audio_analyses")
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
class InterviewVideoAnalyze(Base):
    __tablename__ = "interview_video_analyze"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(String(50), ForeignKey("interviews.id"), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)  # 예: 2025-08-06T20:13:15
    emotion = Column(String(50), nullable=False)       # 예측 감정 (자신감, 불안정 등)
    raw_emotion = Column(String(50), nullable=True)    # 원본 감정 (예: DeepFace 결과)
    confidence = Column(Float, nullable=True)          # 감정 신뢰도 (0~1)

    blink_count = Column(Integer, nullable=True)       # 눈 깜빡임 횟수
    posture = Column(String(50), nullable=True)        # 자세 상태 ("정상", "불안정")

    gaze_x = Column(Float, nullable=True)              # 시선 X
    gaze_y = Column(Float, nullable=True)              # 시선 Y

    head_pose = Column(JSON, nullable=True)            # 머리 위치 [x, y, z]
    ear = Column(Float, nullable=True)                 # 눈 비율 (EAR)
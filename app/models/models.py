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

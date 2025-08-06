from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base


class Interview(Base):
    __tablename__ = "interview"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64), nullable=False)
    job_position = Column(String(255), nullable=False)
    job_url = Column(String(1024))
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계 설정
    text_analyses = relationship("InterviewTextAnalyze", back_populates="interview", cascade="all, delete-orphan")
    audio_analyses = relationship("InterviewAudioAnalyze", back_populates="interview", cascade="all, delete-orphan")


class InterviewTextAnalyze(Base):
    __tablename__ = "interview_txt_analyze"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interview.id", ondelete="CASCADE"))
    question_number = Column(Integer, nullable=False)  # 질문 번호 (1, 2, 3, ...)
    question_text = Column(String(1000), nullable=False)
    answer_text = Column(String(3000), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    interview = relationship("Interview", back_populates="text_analyses")


class InterviewAudioAnalyze(Base):
    __tablename__ = "interview_audio_analyze"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interview.id", ondelete="CASCADE"))
    question_number = Column(Integer, nullable=False)
    emotion = Column(String(255), nullable=False)
    probabilities_json = Column(String(4000))  # JSON 문자열 형태로 감정 확률 저장
    created_at = Column(DateTime, default=datetime.utcnow)

    # 관계
    interview = relationship("Interview", back_populates="audio_analyses")

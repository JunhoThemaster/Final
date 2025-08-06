// src/api/interview.ts
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_INTERVIEW_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface InterviewSetupRequest {
  job_position: string;
  num_questions: number;
}

export interface InterviewSetupResponse {
  session_id: string;
  questions: string[];
  job_position: string;
  message: string;
}

export interface SpeechAnalysisResponse {
  session_id: string;
  question_index: number;
  text: string;
  confidence: number;
  emotion: string;
  
  // CSV 30개 컬럼
  jitter_local: number;
  jitter_rap: number;
  jitter_ppq5: number;
  shimmer_local: number;
  shimmer_apq3: number;
  shimmer_apq5: number;
  voice_breaks: number;
  intensity_mean_db: number;
  intensity_max_db: number;
  intensity_min_db: number;
  rms_intensity_db: number;
  syllable_duration: number;
  speech_rate: number;
  articulation_rate: number;
  pause_duration: number;
  pause_number: number;
  spectral_slope: number;
  f0_mean: number;
  f0_std: number;
  f0_min: number;
  f0_max: number;
  pitch_period_mean: number;
  voicing_fraction: number;
  unvoicing_fraction: number;
  mean_harmonicity: number;
  duration: number;
  
  // 계산된 지표들
  speech_clarity: number;
  vocal_stability: number;
  prosody_score: number;
  overall_score: number;
  end_detected: boolean;
  
  // 맥락 분석 필드들 (추가)
  context_matching: number;
  semantic_similarity: number;
  keyword_overlap: number;
  intent_matching: number;
  question_type: string;
  context_grade: string;
  recommendations: string[];
}

export interface FinalFeedbackResponse {
  session_id: string;
  overall_score: number;
  individual_scores: number[];
  delivery_feedback: string;
  tone_feedback: string;
  rhythm_feedback: string;
  strengths: string[];
  improvement_areas: string[];
  recommendations: string[];
  detailed_analysis: any;
}

export const interviewAPI = {
  // 면접 세션 시작
  setupInterview: async (jobPosition: string, numQuestions: number): Promise<InterviewSetupResponse> => {
    const response = await api.post('/api/interview/setup', {
      job_position: jobPosition,
      num_questions: numQuestions
    });
    return response.data;
  },

  // 음성 분석
  analyzeAudio: async (sessionId: string, questionIndex: number, audioBlob: Blob): Promise<SpeechAnalysisResponse> => {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'audio.wav');
    
    const response = await api.post(
      `/api/speech/analyze/${sessionId}?question_index=${questionIndex}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    );
    return response.data;
  },

  // 최종 피드백 생성
  generateFeedback: async (sessionId: string): Promise<FinalFeedbackResponse> => {
    const response = await api.post('/api/feedback/generate', {
      session_id: sessionId
    });
    return response.data;
  },

  // 직무 카테고리 조회
  getJobCategories: async () => {
    const response = await api.get('/api/questions/categories');
    return response.data;
  },
  

  // 세션 정보 조회
  getSessionInfo: async (sessionId: string) => {
    const response = await api.get(`/api/interview/session/${sessionId}`);
    return response.data;
  }
};
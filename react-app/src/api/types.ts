// src/api/types.ts

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

  // CSV 기반 특성
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

  // 계산 지표
  speech_clarity: number;
  vocal_stability: number;
  prosody_score: number;
  overall_score: number;
  end_detected: boolean;

  // 맥락 분석
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

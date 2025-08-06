// src/api/speechAnalysis.ts
import api from './axiosInstance';
import { SpeechAnalysisResponse } from './types';

export const analyzeAudio = async (
  sessionId: string,
  questionIndex: number,
  audioBlob: Blob
): Promise<SpeechAnalysisResponse> => {
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
};

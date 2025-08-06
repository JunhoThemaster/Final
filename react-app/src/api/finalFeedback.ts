// src/api/finalFeedback.ts
import api from './axiosInstance';
import { FinalFeedbackResponse } from './types';

export const generateFeedback = async (
  sessionId: string
): Promise<FinalFeedbackResponse> => {
  const response = await api.post('/api/feedback/generate', {
    session_id: sessionId,
  });
  return response.data;
};

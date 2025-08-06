// src/api/sessionInfo.ts
import api from './axiosInstance';

export const getSessionInfo = async (sessionId: string) => {
  const response = await api.get(`/api/interview/session/${sessionId}`);
  return response.data;
};

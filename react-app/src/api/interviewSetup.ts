// src/api/interviewSetup.ts
import api from './axiosInstance';
import { InterviewSetupResponse } from './types';

export const setupInterview = async (
  jobPosition: string,
  numQuestions: number
): Promise<InterviewSetupResponse> => {
  const token = localStorage.getItem("token");

  const response = await api.post(
    `/api/user/interview/setup/${jobPosition}/${numQuestions}`,
    null,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
};


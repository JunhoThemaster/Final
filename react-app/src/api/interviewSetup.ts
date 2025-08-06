// src/api/interviewSetup.ts
import api from './axiosInstance';
import { InterviewSetupResponse } from './types';

// 수정된 setupInterview.ts
export const setupInterview = async (
  jobPosition: string,
  jobUrl: string,
  numQuestions: number
): Promise<InterviewSetupResponse> => {
  const token = localStorage.getItem("token");

  const response = await api.post(
    `/api/user/interview/setup/${jobPosition}/${numQuestions}`,
    { jobUrl },  // ✅ body에 포함
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );
  return response.data;
};


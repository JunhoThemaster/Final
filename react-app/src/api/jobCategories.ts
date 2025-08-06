// src/api/jobCategories.ts
import api from './axiosInstance';

export const getJobCategories = async () => {
  const response = await api.get('/api/user/questions/categories');
  return response.data;
};

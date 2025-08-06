// src/api/axiosInstance.ts
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_INTERVIEW_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;

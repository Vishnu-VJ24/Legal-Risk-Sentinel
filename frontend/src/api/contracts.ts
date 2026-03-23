import { AxiosError } from 'axios';
import { apiClient } from './client';
import type { AnalysisResult, AnalyzeResponse } from '../types/contracts';

export const checkApiHealth = async (): Promise<{ status: string }> => {
  const { data } = await apiClient.get<{ status: string }>('/health');
  return data;
};

export const uploadContract = async (file: File): Promise<AnalyzeResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<AnalyzeResponse>('/api/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
};

export const fetchResults = async (sessionId: string): Promise<AnalysisResult | null> => {
  try {
    const { data } = await apiClient.get<AnalysisResult>(`/api/results/${sessionId}`);
    return data;
  } catch (error) {
    const axiosError = error as AxiosError;
    if (axiosError.response?.status === 202) {
      return null;
    }
    throw error;
  }
};

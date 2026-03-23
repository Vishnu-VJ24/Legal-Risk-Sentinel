import { AxiosError } from 'axios';
import { apiClient } from './client';
import type { AnalysisResult, AnalyzeResponse } from '../types/contracts';

export const checkApiHealth = async (): Promise<{ status: string }> => {
  const { data } = await apiClient.get<{ status: string }>('/health');
  return data;
};

export const uploadContract = async (file: File): Promise<AnalyzeResponse> => {
  console.log('[LexAI] POST /api/analyze fired', {
    name: file.name,
    size: file.size,
    type: file.type,
  });
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<AnalyzeResponse>('/api/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  console.log('[LexAI] POST /api/analyze response', data);
  return data;
};

export const fetchResults = async (sessionId: string): Promise<AnalysisResult | null> => {
  try {
    console.log('[LexAI] GET /api/results polling start', { sessionId });
    const response = await apiClient.get<AnalysisResult | { detail?: string }>(`/api/results/${sessionId}`, {
      validateStatus: (status) => (status >= 200 && status < 300) || status === 202,
    });

    if (response.status === 202) {
      console.log('[LexAI] GET /api/results still processing', {
        sessionId,
        response: response.data,
      });
      return null;
    }

    const data = response.data as AnalysisResult;
    console.log('[LexAI] GET /api/results response', data);
    return data;
  } catch (error) {
    const axiosError = error as AxiosError;
    console.error('[LexAI] GET /api/results error', axiosError);
    throw error;
  }
};

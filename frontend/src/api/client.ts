import type {
  ChatModelsResponse,
  RawEdge,
  RawReportJSON,
  RawRiskAnalysisItem,
  RawSection,
  RunStatusResponse,
} from './types';

const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
export const API_BASE = configuredApiBase && configuredApiBase.length > 0
  ? configuredApiBase.replace(/\/+$/, '')
  : '/api';

async function optionalResult<T>(path: string): Promise<T | null> {
  const response = await fetch(`${API_BASE}${path}`, { cache: 'no-store' });
  if (response.status === 404 || !response.ok) return null;
  return response.json();
}

export async function uploadPDF(file: File): Promise<{ run_id: string; file_name: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE}/upload`, { method: 'POST', body: formData });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }
  return response.json();
}

export async function fetchRunStatus(runId: string): Promise<RunStatusResponse> {
  const response = await fetch(`${API_BASE}/status/${runId}`, { cache: 'no-store' });
  if (!response.ok) throw new Error('Failed to fetch status');
  return response.json();
}

export async function cancelPipeline(runId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/cancel/${runId}`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to cancel pipeline');
}

export function fetchSections(runId: string): Promise<RawSection[] | null> {
  return optionalResult(`/results/${runId}/sections`);
}

export function fetchEdges(runId: string): Promise<RawEdge[] | null> {
  return optionalResult(`/results/${runId}/edges`);
}

export function fetchRisks(runId: string): Promise<RawRiskAnalysisItem[] | null> {
  return optionalResult(`/results/${runId}/risks`);
}

export function fetchReportJSON(runId: string): Promise<RawReportJSON | null> {
  return optionalResult(`/results/${runId}/report-json`);
}

export async function fetchReportMD(runId: string): Promise<string | null> {
  const response = await fetch(`${API_BASE}/results/${runId}/report-md`, { cache: 'no-store' });
  if (response.status === 404 || !response.ok) return null;
  return response.text();
}

export async function fetchChatModels(): Promise<ChatModelsResponse> {
  const response = await fetch(`${API_BASE}/chat/models`, { cache: 'no-store' });
  if (!response.ok) throw new Error('Failed to fetch chat models');
  return response.json();
}

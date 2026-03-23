export type PipelineStage = 'parsing' | 'extracting' | 'scoring' | 'explaining' | 'done';

export type PipelineStatus = 'processing' | 'complete' | 'error';

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface AnalyzeResponse {
  session_id: string;
  status: PipelineStatus;
  pipeline_stage: PipelineStage;
  progress_pct: number;
}

export interface ClauseRiskAxes {
  liability: number;
  indemnity: number;
  ip_rights: number;
  termination: number;
}

export interface ClauseResult {
  id: string;
  type: string;
  text: string;
  page_number: number;
  bbox: [number, number, number, number];
  risk_score: number;
  risk_axes: ClauseRiskAxes;
  risk_level: RiskLevel;
  explanation: string;
  renegotiation_suggestion?: string;
  similar_safe_clause?: string;
}

export interface RiskDistribution {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface AnalysisResult {
  session_id: string;
  document_name: string;
  total_clauses: number;
  overall_risk_score: number;
  processing_time_seconds: number;
  clauses: ClauseResult[];
  risk_distribution: RiskDistribution;
}

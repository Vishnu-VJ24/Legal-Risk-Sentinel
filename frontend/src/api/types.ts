export interface ChatModelDefinition {
  id: string;
  model: string;
  attribute: string;
  display_name: string;
  assistant_name: string;
  max_tokens?: number;
}

export interface ChatModelsResponse {
  models: ChatModelDefinition[];
  default_model_id: string | null;
}

export interface RawSection {
  node_id: string;
  title: string;
  text: string;
  type?: string;
  parent_id?: string | null;
  canonical_id?: string;
  node_type?: string;
  is_analysis_unit?: boolean;
  page_start?: number;
  page_end?: number;
  start_char?: number;
}

export interface RawEdge {
  from: string;
  to: string;
  relations?: string[];
  max_confidence: number;
  evidence_quotes?: string[];
  relation_label?: string;
  relation_labels?: string[];
  relation_label_details?: RelationLabelDetail[];
  label_source?: string;
  sources?: string[];
}

export interface RelationLabelDetail {
  label: string;
  source: string;
  confidence: number;
}

export interface RawRisk {
  section_id: string;
  risk_type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  rationale: string;
  confidence: number;
  evidence: string[];
}

export interface RawReportJSON {
  document_summary?: string;
  executive_summary?: string;
  overall_document_risk?: string;
  overall_risk_score?: string;
  top_risks: TopRiskPreview[];
  all_section_summaries?: Array<Record<string, unknown>>;
  recommended_review_order?: string[];
  generation_mode?: string;
}

export interface RawRiskFlag {
  risk_type?: string;
  severity?: string;
  rationale?: string;
  evidence_quotes?: string[];
}

export interface RawRiskAnalysisItem {
  section_id: string;
  source_clause_ids?: string[];
  title?: string;
  confidence?: number;
  risk_flags?: RawRiskFlag[];
}

export interface TopRiskPreview {
  section_id?: string | null;
  title?: string | null;
  severity?: string | null;
  summary?: string | null;
}

export interface DocumentSummaryState {
  totalSections?: number;
  totalEdges?: number;
  flaggedSections?: number;
  overallRisk?: string | null;
  topRiskPreview?: TopRiskPreview[];
}

export interface NormalizedEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
  relations: string[];
  labelDetails: RelationLabelDetail[];
  sources: string[];
  evidenceQuotes: string[];
}

export interface ContractSection extends RawSection {
  id: string;
  content: string;
  riskInfo?: RawRisk;
  linkedTo: { targetId: string; relation: string }[];
  linkedFrom: { sourceId: string; relation: string }[];
}

export interface DocumentState {
  meta: {
    fileName: string;
    totalSections: number;
    flaggedSections: number;
    totalEdges: number;
    connectedSections: number;
  };
  sectionsMap: Record<string, ContractSection>;
  edges: NormalizedEdge[];
  allRisks: RawRisk[];
  topRisks: RawRisk[];
  reportMarkdown: string | null;
  reportData: RawReportJSON | null;
  summary?: DocumentSummaryState;
}

export type StageProgressKey =
  | 'section_indexing'
  | 'graph_creation'
  | 'risk_analysis'
  | 'report'
  | 'report_race'
  | 'report_reduction';

export interface RunStatusResponse {
  run_id: string;
  file_name: string;
  stage: string;
  status: 'running' | 'complete' | 'error';
  error: string | null;
  stage_detail: string;
  stage_index?: number;
  stage_total?: number;
  progress_percent?: number;
  total_sections?: number | null;
  total_edges?: number | null;
  flagged_sections?: number | null;
  overall_risk?: string | null;
  top_risk_preview?: TopRiskPreview[] | null;
  sections_ready?: boolean;
  edges_ready?: boolean;
  risks_ready?: boolean;
  report_ready?: boolean;
  artifact_warnings?: string[];
  edges_revision?: number;
  risk_revision?: number;
  risk_groups_completed?: number;
  risk_groups_total?: number;
  stage_progress?: {
    stage_key: StageProgressKey;
    label: string;
    completed: number;
    total: number;
    unit: string;
    percent: number;
    current_item_label?: string;
    validated_edges_so_far?: number;
  } | null;
}

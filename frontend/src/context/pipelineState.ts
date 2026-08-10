import {
  normalizeEdges,
  normalizeRisks,
  normalizeSections,
} from '../api/normalizers';
import type {
  DocumentState,
  DocumentSummaryState,
  RawEdge,
  RawReportJSON,
  RawRiskAnalysisItem,
  RawSection,
} from '../api/types';

export type PipelineDataAction =
  | { type: 'reset' }
  | { type: 'summary'; summary: DocumentSummaryState }
  | { type: 'sections'; sections: RawSection[]; fileName: string }
  | { type: 'edges'; edges: RawEdge[]; fileName: string }
  | { type: 'risks'; risks: RawRiskAnalysisItem[]; fileName: string }
  | { type: 'report'; reportData: RawReportJSON | null; reportMarkdown: string };

const emptyMeta = (fileName: string) => ({
  fileName,
  totalSections: 0,
  flaggedSections: 0,
  totalEdges: 0,
  connectedSections: 0,
});

export function pipelineDataReducer(
  state: Partial<DocumentState> | null,
  action: PipelineDataAction,
): Partial<DocumentState> | null {
  if (action.type === 'reset') return null;

  if (action.type === 'summary') {
    return { ...state, summary: { ...state?.summary, ...action.summary } };
  }

  if (action.type === 'sections') {
    const { sectionsMap, totalSections } = normalizeSections(action.sections);
    return {
      ...state,
      sectionsMap,
      meta: {
        ...(state?.meta ?? emptyMeta(action.fileName)),
        totalSections,
      },
      summary: { ...state?.summary, totalSections },
    };
  }

  if (action.type === 'edges') {
    const sectionsMap = Object.fromEntries(
      Object.entries(state?.sectionsMap ?? {}).map(([id, section]) => [
        id,
        { ...section, linkedTo: [], linkedFrom: [] },
      ]),
    );
    const { normalizedEdges, totalEdges, connectedSections } = normalizeEdges(
      action.edges,
      sectionsMap,
    );
    return {
      ...state,
      sectionsMap,
      edges: normalizedEdges,
      meta: {
        ...(state?.meta ?? emptyMeta(action.fileName)),
        totalEdges,
        connectedSections,
      },
      summary: { ...state?.summary, totalEdges },
    };
  }

  if (action.type === 'risks') {
    const sectionsMap = Object.fromEntries(
      Object.entries(state?.sectionsMap ?? {}).map(([id, section]) => [
        id,
        { ...section, riskInfo: undefined },
      ]),
    );
    const { allRisks, topRisks, flaggedSections } = normalizeRisks(
      action.risks,
      sectionsMap,
    );
    return {
      ...state,
      sectionsMap,
      allRisks,
      topRisks,
      meta: {
        ...(state?.meta ?? emptyMeta(action.fileName)),
        flaggedSections,
      },
      summary: {
        ...state?.summary,
        flaggedSections,
        topRiskPreview: topRisks.slice(0, 3).map(risk => ({
          section_id: risk.section_id,
          title: sectionsMap[risk.section_id]?.title ?? null,
          severity: risk.severity,
          summary: risk.rationale,
        })),
      },
    };
  }

  return {
    ...state,
    reportData: action.reportData,
    reportMarkdown: action.reportMarkdown,
    summary: {
      ...state?.summary,
      overallRisk:
        state?.summary?.overallRisk
        ?? action.reportData?.overall_risk_score
        ?? action.reportData?.overall_document_risk
        ?? null,
    },
  };
}

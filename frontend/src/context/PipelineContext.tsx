/* eslint-disable react-refresh/only-export-components */
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
  useState,
} from 'react';
import {
  cancelPipeline,
  fetchEdges,
  fetchReportJSON,
  fetchReportMD,
  fetchRisks,
  fetchRunStatus,
  fetchSections,
  uploadPDF,
} from '../api/client';
import type {
  DocumentState,
  RelationLabelDetail,
  RunStatusResponse,
  StageProgressKey,
} from '../api/types';
import { startSerializedPolling, type SerializedPoller } from '../lib/serializedPoller';
import { pipelineDataReducer } from './pipelineState';
import { getTerminalDecision } from './pipelineStatus';

export type PipelineStage =
  | 'UPLOADED'
  | 'EXTRACTED'
  | 'SECTIONS_BUILT'
  | 'GRAPH_READY'
  | 'RISKS_ANALYZED'
  | 'REPORT_READY';

export type AppView = 'LANDING' | 'DASHBOARD';

export interface SelectedGraphEdge {
  sourceId: string;
  targetId: string;
  count: number;
  relations: string[];
  labelDetails: RelationLabelDetail[];
  sources: string[];
  rawEdgeIds: string[];
  evidenceQuotes: string[];
}

const STAGE_ORDER: PipelineStage[] = [
  'UPLOADED',
  'EXTRACTED',
  'SECTIONS_BUILT',
  'GRAPH_READY',
  'RISKS_ANALYZED',
  'REPORT_READY',
];

const stageIndex = (stage: PipelineStage) => STAGE_ORDER.indexOf(stage);
const isPipelineStage = (stage: string): stage is PipelineStage =>
  STAGE_ORDER.includes(stage as PipelineStage);

interface ProgressMeta {
  stageIndex?: number;
  stageTotal?: number;
  progressPercent?: number;
  stageProgress?: {
    stageKey: StageProgressKey;
    label: string;
    completed: number;
    total: number;
    unit: string;
    percent: number;
    currentItemLabel?: string;
    validatedEdgesSoFar?: number;
  } | null;
}

interface PipelineContextValue {
  view: AppView;
  stage: PipelineStage;
  data: Partial<DocumentState> | null;
  fileName: string | null;
  selectedSectionId: string | null;
  setSelectedSectionId: (id: string | null) => void;
  selectedEdge: SelectedGraphEdge | null;
  setSelectedEdge: (edge: SelectedGraphEdge | null) => void;
  isLoading: boolean;
  startAnalysis: (file: File) => void;
  error: string | null;
  artifactWarnings: string[];
  runId: string | null;
  stopAnalysis: () => Promise<void>;
  stageDetail: string | null;
  progressMeta: ProgressMeta | null;
}

const PipelineContext = createContext<PipelineContextValue | undefined>(undefined);
const POLL_INTERVAL = 1500;

function visibleStage(
  backendStage: PipelineStage,
  fetched: Set<string>,
): PipelineStage {
  if (fetched.has('report')) return 'REPORT_READY';
  if (fetched.has('risks')) return 'RISKS_ANALYZED';
  if (fetched.has('edges')) return 'GRAPH_READY';
  if (fetched.has('sections')) return 'SECTIONS_BUILT';
  return stageIndex(backendStage) <= stageIndex('EXTRACTED')
    ? backendStage
    : 'EXTRACTED';
}

function canShowProgress(status: RunStatusResponse, fetched: Set<string>): boolean {
  const key = status.stage_progress?.stage_key;
  if (!key || key === 'section_indexing') return true;
  if (key === 'graph_creation') return fetched.has('sections');
  if (key === 'risk_analysis') return fetched.has('edges');
  return fetched.has('risks');
}

export const PipelineProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [view, setView] = useState<AppView>('LANDING');
  const [data, dispatchData] = useReducer(pipelineDataReducer, null);
  const [stage, setStage] = useState<PipelineStage>('UPLOADED');
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<SelectedGraphEdge | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [artifactWarnings, setArtifactWarnings] = useState<string[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [stageDetail, setStageDetail] = useState<string | null>(null);
  const [progressMeta, setProgressMeta] = useState<ProgressMeta | null>(null);

  const fetchedRef = useRef(new Set<string>());
  const pollerRef = useRef<SerializedPoller | null>(null);
  const edgesRevisionRef = useRef(-1);
  const riskRevisionRef = useRef(-1);

  const stopPolling = useCallback(() => {
    pollerRef.current?.stop();
    pollerRef.current = null;
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const stopAnalysis = useCallback(async () => {
    if (!runId) return;
    try {
      await cancelPipeline(runId);
    } catch (cancelError) {
      console.warn('Failed to send cancel signal:', cancelError);
    }
    stopPolling();
    setIsLoading(false);
    setError('Analysis stopped by user.');
  }, [runId, stopPolling]);

  const applyStatus = useCallback((status: RunStatusResponse) => {
    const backendStage = isPipelineStage(status.stage) ? status.stage : 'UPLOADED';
    const displayedStage = visibleStage(backendStage, fetchedRef.current);
    const showProgress = canShowProgress(status, fetchedRef.current);
    setArtifactWarnings(status.artifact_warnings ?? []);
    setProgressMeta({
      stageIndex: stageIndex(displayedStage) + 1,
      stageTotal: status.stage_total,
      progressPercent: Math.min(
        status.progress_percent ?? 100,
        Math.round(((stageIndex(displayedStage) + 1) / STAGE_ORDER.length) * 100),
      ),
      stageProgress: status.stage_progress && showProgress
        ? {
            stageKey: status.stage_progress.stage_key,
            label: status.stage_progress.label,
            completed: status.stage_progress.completed,
            total: status.stage_progress.total,
            unit: status.stage_progress.unit,
            percent: status.stage_progress.percent,
            currentItemLabel: status.stage_progress.current_item_label,
            validatedEdgesSoFar: status.stage_progress.validated_edges_so_far,
          }
        : null,
    });
    dispatchData({
      type: 'summary',
      summary: {
        totalSections: status.total_sections ?? undefined,
        totalEdges: status.total_edges ?? undefined,
        flaggedSections: status.flagged_sections ?? undefined,
        overallRisk: status.overall_risk ?? undefined,
        topRiskPreview: status.top_risk_preview ?? undefined,
      },
    });
    if (stageIndex(backendStage) <= stageIndex('EXTRACTED')) {
      setStage(current => stageIndex(backendStage) > stageIndex(current) ? backendStage : current);
      setStageDetail(status.stage_detail || null);
    }
  }, []);

  const startAnalysis = useCallback(async (file: File) => {
    stopPolling();
    setFileName(file.name);
    setView('DASHBOARD');
    setIsLoading(true);
    setStage('UPLOADED');
    dispatchData({ type: 'reset' });
    setRunId(null);
    setSelectedSectionId(null);
    setSelectedEdge(null);
    setError(null);
    setArtifactWarnings([]);
    setStageDetail('PDF received, starting pipeline...');
    setProgressMeta(null);
    fetchedRef.current = new Set();
    edgesRevisionRef.current = -1;
    riskRevisionRef.current = -1;

    try {
      const { run_id } = await uploadPDF(file);
      setRunId(run_id);

      const poll = async (): Promise<boolean> => {
        const status = await fetchRunStatus(run_id);
        const fetchedAtStart = new Set(fetchedRef.current);
        applyStatus(status);

        if (status.sections_ready && !fetchedRef.current.has('sections')) {
          const sections = await fetchSections(run_id);
          if (sections) {
            dispatchData({ type: 'sections', sections, fileName: file.name });
            fetchedRef.current.add('sections');
            setStage('SECTIONS_BUILT');
            setStageDetail('Sections are ready. Building the clause relationship map...');
          }
        }

        if (
          status.edges_ready
          && fetchedAtStart.has('sections')
          && (
            !fetchedRef.current.has('edges')
            || (status.edges_revision ?? 0) > edgesRevisionRef.current
          )
        ) {
          const edges = await fetchEdges(run_id);
          if (edges) {
            dispatchData({ type: 'edges', edges, fileName: file.name });
            fetchedRef.current.add('edges');
            edgesRevisionRef.current = status.edges_revision ?? 0;
            setStage('GRAPH_READY');
            setStageDetail('Clause relationships are ready. Starting risk analysis...');
          }
        }

        if (
          status.risks_ready
          && fetchedAtStart.has('edges')
          && (
            !fetchedRef.current.has('risks')
            || (status.risk_revision ?? 0) > riskRevisionRef.current
          )
        ) {
          const risks = await fetchRisks(run_id);
          if (risks) {
            dispatchData({ type: 'risks', risks, fileName: file.name });
            fetchedRef.current.add('risks');
            riskRevisionRef.current = status.risk_revision ?? 0;
            setStage('RISKS_ANALYZED');
            setStageDetail('Risk findings are ready. Preparing the executive report...');
          }
        }

        if (
          status.report_ready
          && fetchedAtStart.has('risks')
          && !fetchedRef.current.has('report')
        ) {
          const [reportData, reportMarkdown] = await Promise.all([
            fetchReportJSON(run_id),
            fetchReportMD(run_id),
          ]);
          if (reportMarkdown) {
            dispatchData({ type: 'report', reportData, reportMarkdown });
            fetchedRef.current.add('report');
            setStage('REPORT_READY');
            setStageDetail('Analysis complete.');
          }
        }

        const terminalDecision = getTerminalDecision(
          status,
          fetchedRef.current.has('report'),
        );
        if (terminalDecision === 'error') {
          setIsLoading(false);
          setError(status.error || 'Pipeline failed');
          return false;
        }
        if (terminalDecision === 'complete') {
          setIsLoading(false);
          if (!status.report_ready && !(status.artifact_warnings?.length)) {
            setArtifactWarnings(['Analysis completed, but the executive report is unavailable.']);
          }
          return false;
        }
        return true;
      };

      pollerRef.current = startSerializedPolling(
        poll,
        POLL_INTERVAL,
        pollingError => console.error('Polling error:', pollingError),
      );
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload failed');
      setIsLoading(false);
    }
  }, [applyStatus, stopPolling]);

  return (
    <PipelineContext.Provider value={{
      view,
      stage,
      data,
      fileName,
      selectedSectionId,
      setSelectedSectionId,
      selectedEdge,
      setSelectedEdge,
      isLoading,
      startAnalysis,
      stopAnalysis,
      error,
      artifactWarnings,
      runId,
      stageDetail,
      progressMeta,
    }}>
      {children}
    </PipelineContext.Provider>
  );
};

export const usePipeline = () => {
  const context = useContext(PipelineContext);
  if (!context) throw new Error('usePipeline must be used within a PipelineProvider');
  return context;
};

import React from 'react';
import { AlertTriangle, FileText, Link2, Shield, Square } from 'lucide-react';
import { usePipeline } from '../context/PipelineContext';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

const STAGES = [
  'UPLOADED',
  'EXTRACTED',
  'SECTIONS_BUILT',
  'GRAPH_READY',
  'RISKS_ANALYZED',
  'REPORT_READY',
] as const;

export const Header: React.FC = () => {
  const { stage, fileName, isLoading, stopAnalysis, stageDetail, progressMeta, data, artifactWarnings } = usePipeline();
  const stageProgress = progressMeta?.stageProgress;

  const getStageLabel = () => {
    switch (stage) {
      case 'UPLOADED': return 'Extracting Text...';
      case 'EXTRACTED': return 'Segmenting Clauses...';
      case 'SECTIONS_BUILT': return 'Mapping Clauses...';
      case 'GRAPH_READY': return 'Analyzing Risks...';
      case 'RISKS_ANALYZED': return 'Generating Report...';
      case 'REPORT_READY': return 'Analysis Complete';
      default: return 'Pending';
    }
  };

  const stageColor = stage === 'REPORT_READY' ? 'default' : 'secondary';
  const currentStageIndex = STAGES.indexOf(stage);
  const progressPercent = progressMeta?.progressPercent ?? Math.round(((currentStageIndex + 1) / STAGES.length) * 100);
  const summary = data?.summary;
  const meta = data?.meta;
  const metrics = [
    { label: 'Clauses', value: summary?.totalSections ?? meta?.totalSections, icon: FileText },
    { label: 'Links', value: summary?.totalEdges ?? meta?.totalEdges, icon: Link2 },
    { label: 'Flagged', value: summary?.flaggedSections ?? meta?.flaggedSections, icon: AlertTriangle },
  ].filter(metric => metric.value !== undefined && metric.value !== null);

  return (
    <header className="z-30 border-b border-slate-200 bg-[linear-gradient(180deg,#ffffff,#f8fbff)] px-5 py-3 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <div className="rounded-xl bg-[linear-gradient(135deg,#0f172a,#1d4ed8)] p-2 text-white shadow-lg shadow-sky-100">
              <Shield size={16} />
            </div>
            <div className="min-w-0">
              <h1 className="text-base font-semibold tracking-tight text-slate-900">Legal Sentinel</h1>
              <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                <span className="flex items-center">
                  <FileText size={13} className="mr-1.5 shrink-0" />
                  <span className="max-w-[260px] truncate">{fileName || 'Contract.pdf'}</span>
                </span>
                <Badge variant="outline" className="border-sky-200 bg-sky-50 text-[10px] uppercase tracking-[0.18em] text-sky-700">
                  Demo Build
                </Badge>
              </div>
            </div>
            {metrics.length > 0 && (
              <div className="ml-0 flex flex-wrap items-center gap-2 xl:ml-4">
                {metrics.map(({ label, value, icon: Icon }) => (
                  <div
                    key={label}
                    className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-700 shadow-sm"
                  >
                    <Icon size={12} className="text-slate-500" />
                    <span className="uppercase tracking-[0.14em] text-slate-500">{label}:</span>
                    <span className="font-semibold text-slate-900">{value}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            {isLoading && (
              <Button
                variant="outline"
                size="sm"
                onClick={stopAnalysis}
                className="h-8 rounded-full border-red-200 text-xs text-red-600 hover:bg-red-50"
              >
                <Square className="mr-1.5 h-3 w-3" />
                Stop Analysis
              </Button>
            )}
            <Badge variant={stageColor} className="border border-slate-900 bg-slate-900 px-3 py-1 text-xs font-semibold text-white shadow-sm">
              {getStageLabel()}
            </Badge>
          </div>
          <p className="text-[11px] font-medium text-slate-500">{progressPercent}% complete</p>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-2 overflow-x-auto pb-0.5">
        <p className="mr-2 whitespace-nowrap text-[11px] font-medium text-slate-500">
          {stageDetail || 'Preparing the contract analysis workspace.'}
        </p>
        {STAGES.map((stageId, index) => {
          const isComplete = index < currentStageIndex || (index === currentStageIndex && stage === 'REPORT_READY' && !isLoading);
          const isCurrent = index === currentStageIndex;
          const shortLabel = stageId === 'UPLOADED'
            ? 'Upload'
            : stageId === 'EXTRACTED'
              ? 'Text'
              : stageId === 'SECTIONS_BUILT'
                ? 'Sections'
                : stageId === 'GRAPH_READY'
                  ? 'Graph'
                  : stageId === 'RISKS_ANALYZED'
                    ? 'Risks'
                    : 'Report';

          return (
            <React.Fragment key={stageId}>
              <div
                className={cn(
                  'flex min-w-[84px] items-center gap-1.5 rounded-full border px-2.5 py-1.5 text-[11px] font-medium transition-colors',
                  isComplete && 'border-emerald-200 bg-emerald-50 text-emerald-700',
                  isCurrent && !isComplete && 'border-sky-200 bg-sky-50 text-sky-700',
                  !isComplete && !isCurrent && 'border-slate-200 bg-white text-slate-400'
                )}
              >
                <span
                  className={cn(
                    'inline-flex h-4 w-4 items-center justify-center rounded-full text-[9px] font-bold',
                    isComplete && 'bg-emerald-600 text-white',
                    isCurrent && !isComplete && 'bg-sky-600 text-white',
                    !isComplete && !isCurrent && 'bg-slate-100 text-slate-500'
                  )}
                >
                  {index + 1}
                </span>
                <span className="truncate">{shortLabel}</span>
              </div>
              {index < STAGES.length - 1 && (
                <div className={cn('h-px min-w-6 flex-1', index < currentStageIndex ? 'bg-emerald-300' : 'bg-slate-200')} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {isLoading && stageProgress && stageProgress.total > 0 && (
        <div className="mt-3 rounded-2xl border border-sky-100 bg-[linear-gradient(180deg,#f8fbff,#f1f7ff)] p-3 shadow-sm">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-sky-700">
                {stageProgress.stageKey === 'section_indexing'
                  ? 'Preparing Sections'
                  : stageProgress.stageKey === 'graph_creation'
                    ? 'Building Clause Graph'
                    : stageProgress.stageKey === 'report'
                      || stageProgress.stageKey === 'report_race'
                      || stageProgress.stageKey === 'report_reduction'
                        ? 'Finalizing Executive Report'
                        : 'Analyzing Clause Risks'}
              </p>
              <p className="mt-0.5 text-sm font-semibold text-slate-900">{stageProgress.label}</p>
            </div>
            <div className="text-left sm:text-right">
              <p className="text-sm font-semibold text-slate-900">
                {stageProgress.completed} / {stageProgress.total} {stageProgress.unit}
              </p>
              <p className="text-[11px] font-medium text-slate-500">{stageProgress.percent}%</p>
            </div>
          </div>

          <div className="mt-3 h-2 overflow-hidden rounded-full bg-sky-100">
            <div
              className="h-full rounded-full bg-[linear-gradient(90deg,#38bdf8,#2563eb)] transition-[width] duration-500 ease-out"
              style={{ width: `${Math.max(0, Math.min(100, stageProgress.percent))}%` }}
            />
          </div>

          <div className="mt-2 flex flex-col gap-1 text-[11px] text-slate-500 sm:flex-row sm:items-center sm:justify-between">
            <p>{stageProgress.currentItemLabel || 'Working through queued items...'}</p>
            {stageProgress.stageKey === 'graph_creation' && typeof stageProgress.validatedEdgesSoFar === 'number' && (
              <p>{stageProgress.validatedEdgesSoFar} verified edges collected</p>
            )}
          </div>
        </div>
      )}
      {artifactWarnings.length > 0 && (
        <div className="mt-2 flex items-start gap-2 border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <p>{artifactWarnings.join(' ')}</p>
        </div>
      )}
    </header>
  );
};

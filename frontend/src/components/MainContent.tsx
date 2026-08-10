import React, { lazy, Suspense } from 'react';
import { LoaderCircle, Map } from 'lucide-react';
import { usePipeline } from '../context/PipelineContext';
import { cn } from '../lib/utils';

const ContractGraph = lazy(() => import('./ContractGraph').then(module => ({ default: module.ContractGraph })));

interface MainContentProps { mobile?: boolean; }

export const MainContent: React.FC<MainContentProps> = ({ mobile = false }) => {
  const { stage, data, setSelectedSectionId, selectedSectionId, setSelectedEdge, isLoading, runId, stageDetail, progressMeta } = usePipeline();
  const readyForGraph = !!data?.sectionsMap;
  const percent = Math.max(2, Math.min(100, progressMeta?.progressPercent ?? 5));
  const stageProgress = progressMeta?.stageProgress;

  return (
    <div className={cn('relative flex flex-1 flex-col overflow-hidden bg-slate-50', mobile && 'min-h-[28rem] rounded-lg border border-slate-200 bg-white shadow-sm')}>
      <div className="flex-1 h-full w-full min-w-0">
        {readyForGraph && stage !== 'UPLOADED' ? (
          <Suspense fallback={<div className="h-full w-full animate-pulse bg-slate-50" />}>
            <ContractGraph data={data} onNodeClick={setSelectedSectionId} onEdgeSelect={setSelectedEdge} selectedId={selectedSectionId} />
          </Suspense>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400"><Map size={28} /></div>
        )}
      </div>
      {!runId && isLoading && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-white/88 p-6 backdrop-blur-[2px]" aria-live="polite">
          <div className="w-full max-w-md border border-slate-200 bg-white p-5 shadow-lg">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center bg-sky-50 text-sky-700"><LoaderCircle className="animate-spin" size={20} /></div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900">{runId ? 'Reviewing contract' : 'Uploading document'}</p>
                <p className="mt-0.5 truncate text-xs text-slate-500">{stageDetail || 'Preparing analysis...'}</p>
              </div>
            </div>
            <div className="mt-5 h-2 overflow-hidden bg-slate-100">
              {runId ? <div className="h-full bg-sky-600 transition-[width] duration-500" style={{ width: `${percent}%` }} /> : <div className="h-full w-2/5 animate-[pulse_1.2s_ease-in-out_infinite] bg-sky-600" />}
            </div>
            <div className="mt-2 flex justify-between text-xs text-slate-500"><span>{stageProgress?.label || (runId ? 'Pipeline in progress' : 'Sending PDF securely')}</span><span>{runId ? `${percent}%` : 'Uploading'}</span></div>
            {stageProgress && <p className="mt-2 text-xs text-slate-500">{stageProgress.completed} / {stageProgress.total} {stageProgress.unit}</p>}
          </div>
        </div>
      )}
    </div>
  );
};

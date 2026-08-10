import React, { lazy, Suspense, useState } from 'react';
import { Group as PanelGroup, Panel, usePanelRef } from 'react-resizable-panels';
import { AlertCircle, AlignLeft, X } from 'lucide-react';
import { usePipeline } from '../context/PipelineContext';
import { useMediaQuery } from '../lib/useMediaQuery';
import { PRIMARY_PANEL_SIZE, SECONDARY_PANEL_SIZE } from '../lib/layout';
import { cn, getSeverityCardStyles } from '../lib/utils';
import { ResizableDivider } from './ResizableDivider';
import { ReportUnavailable, RiskFindings, SelectedClauseCard } from './ReviewViews';
import { ScrollArea } from './ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

const ChatPanel = lazy(() => import('./ChatPanel').then(module => ({ default: module.ChatPanel })));
const FinalReport = lazy(() => import('./FinalReport').then(module => ({ default: module.FinalReport })));

const LoadingPane = () => <div className="h-full w-full animate-pulse bg-slate-50" />;

export const ReviewContent: React.FC = () => {
  const {
    stage,
    data,
    selectedSectionId,
    setSelectedSectionId,
    artifactWarnings,
    runId,
  } = usePipeline();
  const desktop = useMediaQuery('(min-width: 1024px)');
  const [dismissedSectionId, setDismissedSectionId] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<'findings' | 'report' | 'chat'>('findings');
  const chatPanelRef = usePanelRef();
  const reviewReady = ['RISKS_ANALYZED', 'REPORT_READY'].includes(stage) && Boolean(data?.topRisks);

  if (!reviewReady || !data?.topRisks) {
    return (
      <div className="flex w-full flex-1 flex-col items-center justify-center bg-slate-50/30 p-8 text-center text-muted-foreground">
        <div className="mb-4 h-16 w-16 animate-spin rounded-full border-4 border-muted border-t-primary" />
        <p className="text-base font-medium">Analyzing risks and compiling the executive review...</p>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground/60">The review workspace unlocks once clause risk scoring starts returning results.</p>
      </div>
    );
  }

  const selectedSection = selectedSectionId && data.sectionsMap
    ? data.sectionsMap[selectedSectionId] ?? null
    : null;
  const selectSection = (id: string) => {
    setSelectedSectionId(id);
    setDismissedSectionId(null);
  };
  const showInspector = Boolean(
    selectedSectionId && selectedSectionId !== dismissedSectionId,
  );
  const ensureChatPaneWidth = () => {
    const panel = chatPanelRef.current;
    if (panel && panel.getSize().asPercentage < 40) panel.resize('40%');
  };
  const report = data.reportMarkdown
    ? <Suspense fallback={<LoadingPane />}><FinalReport data={data} /></Suspense>
    : <ReportUnavailable warnings={artifactWarnings} />;

  if (!desktop) {
    return (
      <div className="flex flex-1 flex-col overflow-hidden bg-[linear-gradient(180deg,rgba(255,255,255,0.92),rgba(248,250,252,0.88))]">
        <div className="border-b border-slate-200 bg-background/95 p-3 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-slate-900">Review Workspace</p>
            <span className="text-xs font-medium text-muted-foreground">{data.topRisks.length} Priority Risks</span>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {(['findings', 'report', 'chat'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setMobileTab(tab)}
                className={cn(
                  'rounded-xl border px-3 py-2 text-xs font-semibold capitalize transition-colors',
                  mobileTab === tab ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600',
                )}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-3">
          {mobileTab === 'findings' && (
            <div className="space-y-3">
              <RiskFindings risks={data.topRisks} onSelect={selectSection} compact />
              <SelectedClauseCard section={selectedSection} />
            </div>
          )}
          {mobileTab === 'report' && <div className="pb-16">{report}</div>}
          {mobileTab === 'chat' && (
            <div className="h-[70dvh] overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
              <Suspense fallback={<LoadingPane />}><ChatPanel key={runId ?? 'chat'} onResponseStart={ensureChatPaneWidth} /></Suspense>
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <PanelGroup orientation="horizontal" className="h-full min-h-0 w-full flex-1 overflow-hidden" resizeTargetMinimumSize={{ coarse: 24, fine: 12 }}>
      <Panel {...PRIMARY_PANEL_SIZE} className="relative flex min-h-0 min-w-0 flex-col bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(248,250,252,0.85))]">
        <Tabs defaultValue="findings" className="flex min-h-0 flex-1 flex-col overflow-hidden pt-4">
          <div className="z-10 flex items-center justify-between bg-background/90 px-6 pb-2 backdrop-blur">
            <TabsList className="bg-slate-100/80">
              <TabsTrigger value="findings" className="px-4 text-xs">Risk Findings</TabsTrigger>
              <TabsTrigger value="report" className="px-4 text-xs">Executive Report</TabsTrigger>
            </TabsList>
            <div className="px-2 text-xs font-medium text-muted-foreground">{data.topRisks.length} Priority Risks</div>
          </div>
          <TabsContent value="findings" className="mt-0 flex-1 overflow-y-auto outline-none">
            <div className="w-full p-8 pb-20"><RiskFindings risks={data.topRisks} onSelect={selectSection} /></div>
          </TabsContent>
          <TabsContent value="report" className="mt-0 flex-1 content-start overflow-y-auto p-8 outline-none">
            <div className="w-full">{report}</div>
          </TabsContent>
        </Tabs>
      </Panel>
      <ResizableDivider label="Resize review assistant panel" />
      <Panel panelRef={chatPanelRef} {...SECONDARY_PANEL_SIZE} className="z-20 flex min-h-0 min-w-0 flex-col border-l border-slate-200 bg-background shadow-xl">
        <div className={cn('flex flex-col overflow-hidden transition-all duration-300', showInspector ? 'h-[60%]' : 'h-full')}>
          <div className="shrink-0 border-b bg-muted/20 p-3 text-sm font-semibold text-foreground">Ask About This Contract</div>
          <div className="flex-1 overflow-hidden">
            <Suspense fallback={<LoadingPane />}><ChatPanel key={runId ?? 'chat'} onResponseStart={ensureChatPaneWidth} /></Suspense>
          </div>
        </div>
        {showInspector && (
          <div className="flex h-[40%] shrink-0 flex-col border-t bg-card">
            <div className="flex shrink-0 items-center justify-between border-b bg-muted/20 px-4 py-2 shadow-sm">
              <div className="flex items-center text-sm font-semibold"><AlignLeft size={16} className="mr-2 text-muted-foreground" />Clause Details</div>
              <button onClick={() => setDismissedSectionId(selectedSectionId)} className="rounded-md p-1 text-muted-foreground transition-colors hover:bg-muted" title="Close Inspector"><X size={16} /></button>
            </div>
            <ScrollArea className="flex-1 bg-background p-4">
              {selectedSection ? (
                <div className="space-y-4">
                  <SelectedClauseCard section={selectedSection} />
                  {selectedSection.riskInfo && (
                    <div className={cn('rounded-lg border p-4', getSeverityCardStyles(selectedSection.riskInfo.severity))}>
                      <div className="mb-2 flex items-center space-x-2"><AlertCircle size={14} /><span className="text-xs font-bold uppercase">{selectedSection.riskInfo.severity} RISK</span></div>
                      <p className="mb-1 text-sm font-semibold">{selectedSection.riskInfo.risk_type}</p>
                      <p className="text-xs opacity-90">{selectedSection.riskInfo.rationale}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex h-full items-center justify-center py-10 text-sm italic text-muted-foreground">Select a risk or section reference.</div>
              )}
            </ScrollArea>
          </div>
        )}
      </Panel>
    </PanelGroup>
  );
};

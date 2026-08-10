import React from 'react';
import { PipelineProvider, usePipeline } from './context/PipelineContext';
import { LandingPage } from './components/LandingPage';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';
import { RightInspector } from './components/RightInspector';
import { MainContent } from './components/MainContent';
import { ReviewContent } from './components/ReviewContent';
import { Group as PanelGroup, Panel } from 'react-resizable-panels';
import { ResizableDivider } from './components/ResizableDivider';
import { useMediaQuery } from './lib/useMediaQuery';
import { PRIMARY_PANEL_SIZE, SECONDARY_PANEL_SIZE } from './lib/layout';

export type CurrentPage = 'MAP' | 'REVIEW';

const AppContent: React.FC = () => {
  const { view } = usePipeline();
  const [currentPage, setCurrentPage] = React.useState<CurrentPage>('MAP');
  const desktop = useMediaQuery('(min-width: 1024px)');


  if (view === 'LANDING') {
    return <LandingPage />;
  }

  return (
    <div className="relative flex h-dvh min-h-0 w-full flex-col overflow-hidden bg-background text-slate-900">
      <Header />
      <div className="relative flex flex-1 overflow-hidden">
        {!desktop ? (
        <div className="flex flex-1 flex-col overflow-y-auto p-3">
          {currentPage === 'MAP' ? (
            <div className="space-y-3">
              <Sidebar currentPage={currentPage} setCurrentPage={setCurrentPage} mobile />
              <MainContent mobile />
              <RightInspector />
            </div>
          ) : (
            <ReviewContent />
          )}
        </div>
        ) : (
        <div className="flex flex-1 overflow-hidden">
          <Sidebar currentPage={currentPage} setCurrentPage={setCurrentPage} />
          {currentPage === 'MAP' ? (
            <PanelGroup orientation="horizontal" className="h-full min-h-0 min-w-0 flex-1" resizeTargetMinimumSize={{ coarse: 24, fine: 12 }}>
              <Panel {...PRIMARY_PANEL_SIZE} className="flex min-h-0 min-w-0 flex-col">
                <MainContent />
              </Panel>
              <ResizableDivider label="Resize clause details panel" />
              <Panel {...SECONDARY_PANEL_SIZE} className="flex min-h-0 min-w-0 flex-col">
                <RightInspector />
              </Panel>
            </PanelGroup>
          ) : (
            <ReviewContent />
          )}
        </div>
        )}
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <PipelineProvider>
      <AppContent />
    </PipelineProvider>
  );
};

export default App;

import React from 'react';
import { usePipeline } from '../context/PipelineContext';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { AlertCircle, Link2 } from 'lucide-react';
import { cn, getSeverityBadgeStyles } from '../lib/utils';

// Circular import removed: using inline string literal union
type CurrentPage = 'MAP' | 'REVIEW';

interface SidebarProps {
  currentPage?: CurrentPage;
  setCurrentPage?: (page: CurrentPage) => void;
  mobile?: boolean;
}

const PriorityRiskButton: React.FC<{
  risk: { section_id: string; risk_type: string; severity: string };
  selected: boolean;
  onSelect: () => void;
}> = ({ risk, selected, onSelect }) => (
  <button
    className={cn(
      "w-full text-left rounded-xl border p-2.5 text-sm transition-all hover:bg-accent",
      selected
        ? "ring-2 ring-primary border-primary bg-primary/5"
        : "border-slate-200 bg-white",
    )}
    onClick={onSelect}
  >
    <div className="flex items-center justify-between mb-0.5">
      <span className="font-mono text-xs text-muted-foreground">{risk.section_id}</span>
      <Badge className={cn("text-[9px] px-1.5 py-0 border font-semibold shadow-sm", getSeverityBadgeStyles(risk.severity))}>
        {risk.severity}
      </Badge>
    </div>
    <p className="text-xs text-muted-foreground line-clamp-1">{risk.risk_type}</p>
  </button>
);

export const Sidebar: React.FC<SidebarProps> = ({ currentPage, setCurrentPage, mobile = false }) => {
  const { data, selectedSectionId, setSelectedSectionId, error } = usePipeline();

  const topRisks = data?.topRisks || [];
  const urgentRisks = topRisks.filter(risk => risk.severity === 'CRITICAL' || risk.severity === 'HIGH');
  const mediumRisks = topRisks.filter(risk => risk.severity === 'MEDIUM');

  return (
    <div
      className={cn(
        "flex flex-col bg-[linear-gradient(180deg,rgba(248,250,252,0.92),rgba(255,255,255,0.92))]",
        mobile
          ? "w-full rounded-3xl border border-slate-200/80 shadow-sm"
          : "h-full w-44 shrink-0 border-r border-slate-200/80"
      )}
    >
      <ScrollArea className={cn("flex-1", mobile && "max-h-none")}>
        <div className={cn(mobile ? "p-4" : "p-4")}>
          {/* Error Display */}
          {error && (
            <div className="mb-6 flex items-start space-x-3 rounded-2xl border border-red-100 bg-red-50 p-4">
              <AlertCircle className="w-5 h-5 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-900 leading-tight">Pipeline Error</p>
                <p className="text-xs text-red-700 mt-1 leading-normal">{error}</p>
              </div>
            </div>
          )}

          {/* Navigation Controls */}
          {setCurrentPage && currentPage && (
            <div className={cn("mb-6 space-y-2", mobile && "mb-5")}>
              <h2 className="text-[11px] font-semibold tracking-widest uppercase text-muted-foreground mb-3">
                Workspace
              </h2>
              <button
                onClick={() => setCurrentPage('MAP')}
                className={cn(
                  "w-full flex items-center rounded-xl border px-2.5 py-2.5 text-xs font-medium transition-all",
                  currentPage === 'MAP'
                    ? "border-sky-700 bg-slate-900 text-white shadow-sm"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                )}
              >
                <Link2 size={14} className="mr-1.5 shrink-0" />
                Clause Relationships
              </button>
              <button
                onClick={() => setCurrentPage('REVIEW')}
                className={cn(
                  "w-full flex items-center rounded-xl border px-2.5 py-2.5 text-xs font-medium transition-all",
                  currentPage === 'REVIEW'
                    ? "border-sky-700 bg-slate-900 text-white shadow-sm"
                    : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                )}
              >
                <AlertCircle size={14} className="mr-1.5 shrink-0" />
                Priority Review
              </button>
            </div>
          )}

          {/* ===== Compact Top Risk Sections ===== */}
          {(urgentRisks.length > 0 || mediumRisks.length > 0) && (
            <div>
              <h2 className="text-[11px] font-semibold tracking-widest uppercase text-muted-foreground mb-3 flex items-center">
                <AlertCircle size={11} className="mr-1.5 text-red-500" />
                Priority Clauses
              </h2>
              {urgentRisks.length > 0 && (
                <div className={cn("space-y-1.5", mobile && "space-y-2")}>
                  {urgentRisks.slice(0, 6).map((risk, idx) => (
                    <PriorityRiskButton
                      key={`${risk.section_id}:${risk.risk_type}:${idx}`}
                      risk={risk}
                      selected={selectedSectionId === risk.section_id}
                      onSelect={() => setSelectedSectionId(risk.section_id)}
                    />
                  ))}
                </div>
              )}
              {mediumRisks.length > 0 && (
                <div className="mt-4">
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-amber-700">
                    Medium priority
                  </p>
                  <div className={cn("space-y-1.5", mobile && "space-y-2")}>
                    {mediumRisks.slice(0, 6).map((risk, idx) => (
                      <PriorityRiskButton
                        key={`${risk.section_id}:${risk.risk_type}:medium:${idx}`}
                        risk={risk}
                        selected={selectedSectionId === risk.section_id}
                        onSelect={() => setSelectedSectionId(risk.section_id)}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};

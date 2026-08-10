import type { ContractSection, DocumentState, RawRisk } from '../api/types';
import { cn, getSeverityBadgeStyles, getSeverityCardStyles } from '../lib/utils';
import { CheckCircle } from 'lucide-react';
import { Badge } from './ui/badge';
import { Card } from './ui/card';

export const RiskFindings: React.FC<{
  risks: RawRisk[];
  onSelect: (id: string) => void;
  compact?: boolean;
}> = ({ risks, onSelect, compact }) => {
  if (risks.length === 0) {
    return (
      <Card className="border-green-200 bg-green-50/50 p-8 text-center">
        <CheckCircle size={32} className="mx-auto mb-3 text-green-500" />
        <h4 className="font-semibold text-green-900">No High-Level Risks Detected</h4>
        <p className="mt-1 text-sm text-green-800/80">Analysis completed without identifying critical dependencies.</p>
      </Card>
    );
  }
  return (
    <div className={cn('grid grid-cols-1', compact ? 'gap-3' : 'gap-4')}>
      {risks.map((risk, index) => (
        <Card
          key={`${risk.section_id}:${risk.risk_type}:${index}`}
          className={cn(
            'cursor-pointer border shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md',
            compact ? 'p-4' : 'p-6',
            getSeverityCardStyles(risk.severity),
          )}
          onClick={() => onSelect(risk.section_id)}
        >
          <div className={cn('flex items-start justify-between', compact ? 'mb-3 gap-3' : 'mb-4')}>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Clause</p>
              <Badge variant="outline" className="mt-2 bg-background/80 font-mono text-sm shadow-sm">{risk.section_id}</Badge>
            </div>
            <Badge className={cn('font-bold shadow-sm', getSeverityBadgeStyles(risk.severity))}>{risk.severity}</Badge>
          </div>
          <h4 className="mb-2 text-base font-semibold uppercase tracking-wide text-slate-900">{risk.risk_type}</h4>
          <p className="text-sm leading-relaxed text-slate-800 opacity-90">{risk.rationale}</p>
          {!compact && risk.evidence?.[0] && (
            <div className="mt-4 rounded-2xl border border-white/60 bg-white/60 px-4 py-3 text-xs italic text-slate-700">
              “{risk.evidence[0]}”
            </div>
          )}
        </Card>
      ))}
    </div>
  );
};

export const SelectedClauseCard: React.FC<{
  section: ContractSection | null;
}> = ({ section }) => {
  if (!section) return null;
  return (
    <Card className="border border-slate-200 bg-white p-4 shadow-sm">
      <h4 className="font-mono text-sm font-bold text-primary">{section.id}</h4>
      <p className="mt-0.5 text-xs text-muted-foreground">{section.title}</p>
      <div className="mt-4 rounded-2xl border bg-muted/50 p-3 font-serif text-sm leading-relaxed whitespace-pre-wrap text-slate-800">
        {section.content}
      </div>
    </Card>
  );
};

export const ReportUnavailable: React.FC<{ warnings?: string[] }> = ({ warnings }) => (
  <Card className="p-8 text-center text-muted-foreground">
    <p>Generative report is currently unavailable.</p>
    {warnings?.map(warning => <p key={warning} className="mt-2 text-xs">{warning}</p>)}
  </Card>
);

export type ReviewDocument = Partial<DocumentState>;

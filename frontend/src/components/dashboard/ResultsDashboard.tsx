import { useEffect, useMemo, useState } from 'react';
import type { AnalysisResult } from '../../types/contracts';
import { useClauseFilter } from '../../hooks/useClauseFilter';
import { ClauseListPanel } from './ClauseListPanel';
import { ExportBar } from './ExportBar';
import { PdfViewerPanel } from './PdfViewerPanel';
import { RiskOverviewPanel } from './RiskOverviewPanel';

interface ResultsDashboardProps {
  documentUrl?: string;
  isPdf?: boolean;
  results: AnalysisResult;
}

export const ResultsDashboard = ({ documentUrl, isPdf, results }: ResultsDashboardProps) => {
  const { clauseTypes, filteredClauses, filters, setFilters } = useClauseFilter(results.clauses);
  const [selectedClauseId, setSelectedClauseId] = useState<string>();

  const selectedClause = useMemo(
    () => filteredClauses.find((clause) => clause.id === selectedClauseId) ?? filteredClauses[0],
    [filteredClauses, selectedClauseId],
  );

  useEffect(() => {
    if (!selectedClause?.id) {
      return;
    }
    document.getElementById(selectedClause.id)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [selectedClause?.id]);

  return (
    <div className="space-y-6">
      <RiskOverviewPanel results={results} />
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <PdfViewerPanel
          clauses={results.clauses}
          documentUrl={documentUrl}
          isPdf={isPdf}
          onSelectClause={setSelectedClauseId}
          selectedClauseId={selectedClause?.id}
        />
        <ClauseListPanel
          clauseTypes={clauseTypes}
          clauses={filteredClauses}
          filters={filters}
          onFilterChange={setFilters}
          selectedClauseId={selectedClause?.id}
        />
      </div>
      <ExportBar results={results} />
    </div>
  );
};

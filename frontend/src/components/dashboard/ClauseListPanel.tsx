import { useMemo } from 'react';
import type { ClauseResult } from '../../types/contracts';
import type { FilterState } from '../../types/ui';
import { ClauseCard } from './ClauseCard';
import { ClauseFilters } from './ClauseFilters';

interface ClauseListPanelProps {
  clauseTypes: string[];
  clauses: ClauseResult[];
  filters: FilterState;
  onFilterChange: (updater: (current: FilterState) => FilterState) => void;
  selectedClauseId?: string;
}

export const ClauseListPanel = ({
  clauseTypes,
  clauses,
  filters,
  onFilterChange,
  selectedClauseId,
}: ClauseListPanelProps) => {
  const sortedClauses = useMemo(() => [...clauses].sort((a, b) => b.risk_score - a.risk_score), [clauses]);

  return (
    <section className="rounded-[28px] border border-border bg-surface/85 p-6">
      <div>
        <h2 className="text-xl font-semibold">Clause Analysis</h2>
        <p className="mt-2 text-sm leading-7 text-text-secondary">
          Inspect the highest-risk provisions first, then filter by clause type or search across explanations.
        </p>
      </div>
      <div className="mt-5">
        <ClauseFilters clauseTypes={clauseTypes} filters={filters} onChange={onFilterChange} />
      </div>
      <div className="mt-6 max-h-[980px] space-y-4 overflow-y-auto pr-1">
        {sortedClauses.map((clause) => (
          <ClauseCard key={clause.id} clause={clause} highlighted={selectedClauseId === clause.id} />
        ))}
      </div>
    </section>
  );
};

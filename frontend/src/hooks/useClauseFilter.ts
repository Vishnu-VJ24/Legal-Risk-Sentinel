import { useMemo, useState } from 'react';
import type { ClauseResult } from '../types/contracts';
import type { FilterState } from '../types/ui';

const initialState: FilterState = {
  search: '',
  riskLevel: 'all',
  clauseType: 'all',
};

export const useClauseFilter = (clauses?: ClauseResult[]) => {
  const [filters, setFilters] = useState<FilterState>(initialState);
  const safeClauses = useMemo(() => clauses ?? [], [clauses]);

  const clauseTypes = useMemo(
    () => Array.from(new Set(safeClauses.map((clause) => clause.type))),
    [safeClauses],
  );

  const filteredClauses = useMemo(
    () =>
      safeClauses.filter((clause) => {
        const search = filters.search.trim().toLowerCase();
        const matchesSearch =
          search.length === 0 ||
          clause.type.toLowerCase().includes(search) ||
          clause.text.toLowerCase().includes(search) ||
          clause.explanation.toLowerCase().includes(search);
        const matchesRisk = filters.riskLevel === 'all' || clause.risk_level === filters.riskLevel;
        const matchesType = filters.clauseType === 'all' || clause.type === filters.clauseType;
        return matchesSearch && matchesRisk && matchesType;
      }),
    [filters, safeClauses],
  );

  return { clauseTypes, filteredClauses, filters, setFilters };
};

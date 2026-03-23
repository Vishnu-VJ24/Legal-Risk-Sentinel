import { useMemo, useState } from 'react';
import type { ClauseResult } from '../types/contracts';
import type { FilterState } from '../types/ui';

const initialState: FilterState = {
  search: '',
  riskLevel: 'all',
  clauseType: 'all',
};

export const useClauseFilter = (clauses: ClauseResult[]) => {
  const [filters, setFilters] = useState<FilterState>(initialState);

  const clauseTypes = useMemo(() => Array.from(new Set(clauses.map((clause) => clause.type))), [clauses]);

  const filteredClauses = useMemo(
    () =>
      clauses.filter((clause) => {
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
    [clauses, filters],
  );

  return { clauseTypes, filteredClauses, filters, setFilters };
};

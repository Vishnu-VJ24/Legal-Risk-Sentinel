import type { FilterState } from '../../types/ui';

interface ClauseFiltersProps {
  clauseTypes: string[];
  filters: FilterState;
  onChange: (updater: (current: FilterState) => FilterState) => void;
}

export const ClauseFilters = ({ clauseTypes, filters, onChange }: ClauseFiltersProps) => {
  return (
    <div className="grid gap-3 md:grid-cols-[1.6fr_1fr_1fr]">
      <input
        value={filters.search}
        onChange={(event) => onChange((current) => ({ ...current, search: event.target.value }))}
        placeholder="Search clauses, explanations, or clause types"
        aria-label="Search clauses"
        className="rounded-2xl border border-border bg-background px-4 py-3 outline-none transition focus:border-primary/60"
      />
      <select
        value={filters.riskLevel}
        onChange={(event) => onChange((current) => ({ ...current, riskLevel: event.target.value as FilterState['riskLevel'] }))}
        aria-label="Filter by risk"
        className="rounded-2xl border border-border bg-background px-4 py-3 outline-none transition focus:border-primary/60"
      >
        <option value="all">All risk levels</option>
        <option value="critical">Critical</option>
        <option value="high">High</option>
        <option value="medium">Medium</option>
        <option value="low">Low</option>
      </select>
      <select
        value={filters.clauseType}
        onChange={(event) => onChange((current) => ({ ...current, clauseType: event.target.value }))}
        aria-label="Filter by clause type"
        className="rounded-2xl border border-border bg-background px-4 py-3 outline-none transition focus:border-primary/60"
      >
        <option value="all">All clause types</option>
        {clauseTypes.map((clauseType) => (
          <option key={clauseType} value={clauseType}>
            {clauseType}
          </option>
        ))}
      </select>
    </div>
  );
};

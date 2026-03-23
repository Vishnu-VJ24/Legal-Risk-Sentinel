import type { RiskLevel } from './contracts';

export interface FilterState {
  search: string;
  riskLevel: RiskLevel | 'all';
  clauseType: string | 'all';
}

import type { RiskLevel } from '../types/contracts';

export const riskLevelStyles: Record<RiskLevel, string> = {
  low: 'border-risk-low/30 bg-risk-low/15 text-risk-low',
  medium: 'border-risk-medium/30 bg-risk-medium/15 text-risk-medium',
  high: 'border-risk-high/30 bg-risk-high/15 text-risk-high',
  critical: 'border-risk-critical/30 bg-risk-critical/15 text-risk-critical',
};

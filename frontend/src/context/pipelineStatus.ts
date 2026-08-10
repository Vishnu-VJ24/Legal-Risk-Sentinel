import type { RunStatusResponse } from '../api/types';

export type TerminalDecision = 'continue' | 'complete' | 'error';

export function getTerminalDecision(
  status: RunStatusResponse,
  reportLoaded: boolean,
): TerminalDecision {
  if (status.status === 'error') return 'error';
  if (status.status !== 'complete') return 'continue';
  if (status.report_ready && !reportLoaded) return 'continue';
  return 'complete';
}

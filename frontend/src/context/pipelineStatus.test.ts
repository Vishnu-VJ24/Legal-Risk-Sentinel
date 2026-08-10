import { describe, expect, it } from 'vitest';
import type { RunStatusResponse } from '../api/types';
import { getTerminalDecision } from './pipelineStatus';

const status = (overrides: Partial<RunStatusResponse>): RunStatusResponse => ({
  run_id: 'run',
  file_name: 'contract.pdf',
  stage: 'REPORT_READY',
  status: 'running',
  error: null,
  stage_detail: '',
  ...overrides,
});

describe('pipeline terminal status', () => {
  it('stops completed runs when the report is unavailable', () => {
    expect(getTerminalDecision(
      status({ status: 'complete', report_ready: false }),
      false,
    )).toBe('complete');
  });

  it('waits one more poll for a ready report artifact', () => {
    expect(getTerminalDecision(
      status({ status: 'complete', report_ready: true }),
      false,
    )).toBe('continue');
  });

  it('terminates failed runs', () => {
    expect(getTerminalDecision(status({ status: 'error' }), false)).toBe('error');
  });
});

import { describe, expect, it } from 'vitest';
import { startSerializedPolling } from './serializedPoller';

describe('serialized polling', () => {
  it('does not schedule another request after a terminal result', async () => {
    let calls = 0;
    await new Promise<void>((resolve, reject) => {
      startSerializedPolling(
        async () => {
          calls += 1;
          resolve();
          return false;
        },
        1,
        reject,
      );
    });
    await new Promise(resolve => setTimeout(resolve, 5));
    expect(calls).toBe(1);
  });
});

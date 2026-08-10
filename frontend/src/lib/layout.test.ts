import { describe, expect, it } from 'vitest';
import { PRIMARY_PANEL_SIZE, SECONDARY_PANEL_SIZE } from './layout';

describe('desktop panel sizes', () => {
  it('uses percentage strings required by react-resizable-panels', () => {
    expect(PRIMARY_PANEL_SIZE).toEqual({
      defaultSize: '60%',
      minSize: '45%',
      maxSize: '75%',
    });
    expect(SECONDARY_PANEL_SIZE).toEqual({
      defaultSize: '40%',
      minSize: '25%',
      maxSize: '55%',
    });
  });
});

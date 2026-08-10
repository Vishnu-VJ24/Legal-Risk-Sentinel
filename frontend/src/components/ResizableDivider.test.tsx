// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { Group, Panel } from 'react-resizable-panels';
import { describe, expect, it } from 'vitest';
import { ResizableDivider } from './ResizableDivider';

describe('ResizableDivider', () => {
  it('provides an accessible resize target', () => {
    class ResizeObserverMock {
      observe() {}
      unobserve() {}
      disconnect() {}
    }
    globalThis.ResizeObserver = ResizeObserverMock;

    render(
      <Group orientation="horizontal">
        <Panel defaultSize="60%"><div>Primary</div></Panel>
        <ResizableDivider label="Resize details" />
        <Panel defaultSize="40%"><div>Secondary</div></Panel>
      </Group>,
    );

    expect(screen.getByLabelText('Resize details')).toBeTruthy();
  });
});

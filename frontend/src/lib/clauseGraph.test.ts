import { describe, expect, it } from 'vitest';
import type { ContractSection, NormalizedEdge } from '../api/types';
import { aggregateVisibleEdges, buildHierarchy } from './clauseGraph';

const sections: Record<string, ContractSection> = {
  '1': {
    node_id: '1',
    id: '1',
    title: 'One',
    text: 'One',
    content: 'One',
    linkedTo: [],
    linkedFrom: [],
  },
  '2': {
    node_id: '2',
    id: '2',
    title: 'Two',
    text: 'Two',
    content: 'Two',
    linkedTo: [],
    linkedFrom: [],
  },
};

const edge: NormalizedEdge = {
  id: '1->2:0',
  source: '1',
  target: '2',
  relation: 'payment conditioned on',
  relations: ['payment conditioned on', 'notice governed by'],
  labelDetails: [
    { label: 'payment conditioned on', source: 'llm', confidence: 0.9 },
    { label: 'notice governed by', source: 'fallback', confidence: 1 },
  ],
  sources: ['SECTION'],
  evidenceQuotes: ['subject to Section 2'],
};

describe('visible contextual edges', () => {
  it('filters against every underlying contextual label', () => {
    const result = aggregateVisibleEdges(
      [edge],
      ['1', '2'],
      buildHierarchy(sections),
      'notice governed by',
    );

    expect(result.edges).toHaveLength(1);
    expect(result.edges[0].relations).toEqual([
      'payment conditioned on',
      'notice governed by',
    ]);
    expect(result.edges[0].sources).toEqual(['SECTION']);
  });
});

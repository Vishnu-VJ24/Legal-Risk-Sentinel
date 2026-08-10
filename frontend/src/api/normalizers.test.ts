import { describe, expect, it } from 'vitest';
import { normalizeEdges, normalizeRisks, normalizeSections } from './normalizers';

describe('artifact normalizers', () => {
  it('builds contextual edge links', () => {
    const { sectionsMap } = normalizeSections([
      { node_id: '1', title: 'One', text: 'One' },
      { node_id: '2', title: 'Two', text: 'Two' },
    ]);
    normalizeEdges([{
      from: '1',
      to: '2',
      relation_label: 'payment conditioned on',
      relation_labels: ['payment conditioned on', 'notice governed by'],
      relation_label_details: [
        { label: 'payment conditioned on', source: 'llm', confidence: 0.9 },
        { label: 'notice governed by', source: 'fallback', confidence: 1 },
      ],
      label_source: 'llm',
      sources: ['SECTION'],
      max_confidence: 1,
    }], sectionsMap);

    expect(sectionsMap['1'].linkedTo).toEqual([
      { targetId: '2', relation: 'payment conditioned on' },
    ]);
  });

  it('keeps historical relation arrays readable', () => {
    const { sectionsMap } = normalizeSections([
      { node_id: '1', title: 'One', text: 'One' },
      { node_id: '2', title: 'Two', text: 'Two' },
    ]);
    const result = normalizeEdges([{
      from: '1',
      to: '2',
      relations: ['DEPENDENCY'],
      max_confidence: 0.8,
    }], sectionsMap);

    expect(result.normalizedEdges[0].relations).toEqual(['DEPENDENCY']);
    expect(result.normalizedEdges[0].labelDetails[0].source).toBe('legacy');
  });

  it('propagates grouped findings to each affected clause once', () => {
    const { sectionsMap } = normalizeSections([
      { node_id: '1(a)', title: 'A', text: 'A' },
      { node_id: '1(b)', title: 'B', text: 'B' },
    ]);
    const result = normalizeRisks([{
      section_id: '1',
      source_clause_ids: ['1(a)', '1(b)'],
      risk_flags: [{
        risk_type: 'payment',
        severity: 'HIGH',
        rationale: 'Uncertain timing.',
        evidence_quotes: ['promptly'],
      }],
    }], sectionsMap);

    expect(result.allRisks).toHaveLength(2);
    expect(result.flaggedSections).toBe(2);
  });
});

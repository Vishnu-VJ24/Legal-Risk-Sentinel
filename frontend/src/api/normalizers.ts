import type {
  ContractSection,
  NormalizedEdge,
  RawEdge,
  RawRisk,
  RawRiskAnalysisItem,
  RawSection,
} from './types';

export function normalizeSections(
  sections: RawSection[],
): { sectionsMap: Record<string, ContractSection>; totalSections: number } {
  const sectionsMap: Record<string, ContractSection> = {};
  sections.forEach(section => {
    sectionsMap[section.node_id] = {
      ...section,
      id: section.node_id,
      content: section.text,
      linkedTo: [],
      linkedFrom: [],
    };
  });
  return { sectionsMap, totalSections: sections.length };
}

export function normalizeEdges(
  edges: RawEdge[],
  sectionsMap: Record<string, ContractSection>,
): { normalizedEdges: NormalizedEdge[]; totalEdges: number; connectedSections: number } {
  const normalizedEdges: NormalizedEdge[] = [];
  const connectedIds = new Set<string>();

  edges.forEach((edge, index) => {
    const contextualLabels = edge.relation_labels?.filter(Boolean) || [];
    const legacyLabels = edge.relations?.filter(Boolean) || [];
    const relation = edge.relation_label
      || contextualLabels[0]
      || legacyLabels[0]
      || 'explicitly linked';
    const relations = [...new Set([
      relation,
      ...contextualLabels,
      ...legacyLabels,
    ])];
    const labelDetails = edge.relation_label_details?.length
      ? edge.relation_label_details
      : relations.map(label => ({
          label,
          source: edge.label_source || (edge.relations?.length ? 'legacy' : 'fallback'),
          confidence: edge.max_confidence || 0,
        }));
    normalizedEdges.push({
      id: `${edge.from}->${edge.to}:${index}`,
      source: edge.from,
      target: edge.to,
      relation,
      relations,
      labelDetails,
      sources: edge.sources || [],
      evidenceQuotes: edge.evidence_quotes || [],
    });
    connectedIds.add(edge.from);
    connectedIds.add(edge.to);
    sectionsMap[edge.from]?.linkedTo.push({ targetId: edge.to, relation });
    sectionsMap[edge.to]?.linkedFrom.push({ sourceId: edge.from, relation });
  });
  return { normalizedEdges, totalEdges: edges.length, connectedSections: connectedIds.size };
}

export function normalizeRisks(
  risksData: RawRiskAnalysisItem[],
  sectionsMap: Record<string, ContractSection>,
): { allRisks: RawRisk[]; topRisks: RawRisk[]; flaggedSections: number } {
  const allRisks: RawRisk[] = [];
  const seenRiskKeys = new Set<string>();
  const normalizeKeyPart = (value: unknown) =>
    String(value ?? '').trim().toLowerCase().replace(/\s+/g, ' ');

  risksData.forEach(item => {
    const targetIds = item.source_clause_ids?.length
      ? item.source_clause_ids
      : [item.section_id];
    (item.risk_flags || []).forEach(flag => {
      const evidence = flag.evidence_quotes || [];
      const riskKey = [
        normalizeKeyPart(item.section_id),
        normalizeKeyPart(flag.risk_type || 'unknown'),
        normalizeKeyPart(flag.severity || 'LOW'),
        normalizeKeyPart(flag.rationale || ''),
        [...evidence].map(normalizeKeyPart).sort().join('|'),
      ].join('::');
      if (seenRiskKeys.has(riskKey)) return;
      seenRiskKeys.add(riskKey);
      targetIds.forEach(sectionId => allRisks.push({
        section_id: sectionId,
        risk_type: flag.risk_type || 'unknown',
        severity: (flag.severity || 'LOW').toUpperCase() as RawRisk['severity'],
        rationale: flag.rationale || '',
        confidence: item.confidence || 0,
        evidence,
      }));
    });
  });

  const severityOrder: Record<string, number> = {
    CRITICAL: 0,
    HIGH: 1,
    MEDIUM: 2,
    LOW: 3,
  };
  const topRisks = allRisks
    .filter(risk => risk.severity !== 'LOW')
    .sort((left, right) => {
      const severity = (severityOrder[left.severity] ?? 3) - (severityOrder[right.severity] ?? 3);
      if (severity !== 0) return severity;
      if (right.confidence !== left.confidence) return right.confidence - left.confidence;
      return left.section_id.localeCompare(right.section_id);
    });

  allRisks.forEach(risk => {
    const section = sectionsMap[risk.section_id];
    if (!section) return;
    const existing = section.riskInfo;
    if (!existing || severityOrder[risk.severity] < severityOrder[existing.severity]) {
      section.riskInfo = risk;
    }
  });

  return {
    allRisks,
    topRisks,
    flaggedSections: new Set(allRisks.map(risk => risk.section_id)).size,
  };
}

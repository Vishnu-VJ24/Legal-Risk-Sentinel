import { ContractSection, NormalizedEdge, RelationLabelDetail } from '../api/adapter';

export interface HierarchyIndex {
  roots: string[];
  children: Record<string, string[]>;
  parent: Record<string, string | null>;
  descendants: Record<string, string[]>;
  order: Record<string, number>;
}

export interface VisibleEdge {
  id: string;
  source: string;
  target: string;
  relations: string[];
  labelDetails: RelationLabelDetail[];
  sources: string[];
  rawEdgeIds: string[];
  evidenceQuotes: string[];
  count: number;
}

export function buildHierarchy(sections: Record<string, ContractSection>): HierarchyIndex {
  const order: Record<string, number> = {};
  const parent: Record<string, string | null> = {};
  const children: Record<string, string[]> = {};
  Object.values(sections).forEach((section, index) => {
    order[section.id] = section.start_char ?? index;
    parent[section.id] = section.parent_id && sections[section.parent_id] ? section.parent_id : null;
    if (parent[section.id]) (children[parent[section.id]!] ||= []).push(section.id);
  });
  Object.values(children).forEach(ids => ids.sort((a, b) => order[a] - order[b]));
  const roots = Object.keys(sections).filter(id => !parent[id]).sort((a, b) => order[a] - order[b]);
  const descendants: Record<string, string[]> = {};
  const collect = (id: string): string[] => descendants[id] ||= (children[id] || []).flatMap(child => [child, ...collect(child)]);
  Object.keys(sections).forEach(collect);
  return { roots, children, parent, descendants, order };
}

export function getAncestors(id: string | null, hierarchy: HierarchyIndex): string[] {
  if (!id) return [];
  const result: string[] = [];
  let current = hierarchy.parent[id];
  while (current) {
    result.unshift(current);
    current = hierarchy.parent[current];
  }
  return result;
}

export function visibleNodeIds(hierarchy: HierarchyIndex, expanded: Set<string>): string[] {
  const visible: string[] = [];
  const visit = (id: string) => {
    visible.push(id);
    if (expanded.has(id)) (hierarchy.children[id] || []).forEach(visit);
  };
  hierarchy.roots.forEach(visit);
  return visible;
}

function visibleOwner(id: string, visible: Set<string>, hierarchy: HierarchyIndex): string | null {
  let current: string | null | undefined = id;
  while (current && !visible.has(current)) current = hierarchy.parent[current];
  return current || null;
}

export function aggregateVisibleEdges(
  edges: NormalizedEdge[],
  visibleIds: string[],
  hierarchy: HierarchyIndex,
  relationFilter: string,
): { edges: VisibleEdge[]; internalCounts: Record<string, number>; externalCounts: Record<string, number> } {
  const visible = new Set(visibleIds);
  const aggregated = new Map<string, VisibleEdge>();
  const internalCounts: Record<string, number> = {};
  const externalCounts: Record<string, number> = {};
  edges.forEach(edge => {
    if (relationFilter !== 'ALL' && !edge.relations.includes(relationFilter)) return;
    const source = visibleOwner(edge.source, visible, hierarchy);
    const target = visibleOwner(edge.target, visible, hierarchy);
    if (!source || !target) return;
    if (source === target) {
      internalCounts[source] = (internalCounts[source] || 0) + 1;
      return;
    }
    externalCounts[source] = (externalCounts[source] || 0) + 1;
    externalCounts[target] = (externalCounts[target] || 0) + 1;
    const key = `${source}->${target}`;
    const item = aggregated.get(key) || {
      id: key,
      source,
      target,
      relations: [],
      labelDetails: [],
      sources: [],
      rawEdgeIds: [],
      evidenceQuotes: [],
      count: 0,
    };
    item.count += 1;
    item.rawEdgeIds.push(edge.id);
    edge.relations.forEach(relation => {
      if (!item.relations.includes(relation)) item.relations.push(relation);
    });
    edge.labelDetails.forEach(detail => {
      const existing = item.labelDetails.find(value => value.label === detail.label);
      if (!existing) item.labelDetails.push(detail);
      else if (existing.source !== 'llm' && detail.source === 'llm') {
        Object.assign(existing, detail);
      }
    });
    edge.sources.forEach(sourceName => {
      if (!item.sources.includes(sourceName)) item.sources.push(sourceName);
    });
    edge.evidenceQuotes.forEach(quote => {
      if (!item.evidenceQuotes.includes(quote)) item.evidenceQuotes.push(quote);
    });
    aggregated.set(key, item);
  });
  return { edges: [...aggregated.values()], internalCounts, externalCounts };
}

export function focusNeighborhood(
  selectedId: string | null,
  visibleIds: string[],
  edges: VisibleEdge[],
  hierarchy: HierarchyIndex,
): Set<string> {
  if (!selectedId) return new Set(visibleIds);
  const visible = new Set(visibleIds);
  const selectedVisible = visible.has(selectedId)
    ? selectedId
    : [...getAncestors(selectedId, hierarchy)].reverse().find(id => visible.has(id));
  if (!selectedVisible) return new Set(visibleIds);
  const focused = new Set<string>([selectedVisible, ...getAncestors(selectedVisible, hierarchy)]);
  edges.forEach(edge => {
    if (edge.source === selectedVisible) focused.add(edge.target);
    if (edge.target === selectedVisible) focused.add(edge.source);
  });
  const parent = hierarchy.parent[selectedVisible];
  if (parent) (hierarchy.children[parent] || []).forEach(id => {
    if (visible.has(id) && edges.some(edge => edge.source === id || edge.target === id)) focused.add(id);
  });
  return focused;
}

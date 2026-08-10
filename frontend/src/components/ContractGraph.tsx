import React, { useCallback, useMemo, useState } from 'react';
import {
  Background, Controls, Edge, MarkerType, Node, ReactFlow, ReactFlowInstance,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { Crosshair, Filter, Focus, Link2, LocateFixed, Minimize2 } from 'lucide-react';
import { ContractSection, DocumentState } from '../api/adapter';
import {
  aggregateVisibleEdges, buildHierarchy, focusNeighborhood, getAncestors, visibleNodeIds,
} from '../lib/clauseGraph';
import { ClauseMapNode, ClauseNodeData } from './ClauseMapNode';
import { ClauseMapEdge } from './ClauseMapEdge';
import type { SelectedGraphEdge } from '../context/PipelineContext';

interface GraphProps {
  data: Partial<DocumentState>;
  onNodeClick: (id: string) => void;
  onEdgeSelect: (edge: SelectedGraphEdge | null) => void;
  selectedId: string | null;
}

const nodeTypes = { clause: ClauseMapNode };
const edgeTypes = { clause: ClauseMapEdge };
const severityRank: Record<string, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };

function layout(nodes: Node[], hierarchy: ReturnType<typeof buildHierarchy>): Node[] {
  const visible = new Set(nodes.map(node => node.id));
  const byId = new Map(nodes.map(node => [node.id, node]));
  const roots = hierarchy.roots.filter(id => visible.has(id));
  const positions = new Map<string, { x: number; y: number }>();
  // Stable document-order lanes give relationship paths enough room to route
  // without turning the overview into a tightly packed force-directed graph.
  const columns = 3;
  const columnWidth = 440;
  const nodeStep = 196;
  const rowGap = 132;
  let rowY = 38;

  for (let rowStart = 0; rowStart < roots.length; rowStart += columns) {
    const rowRoots = roots.slice(rowStart, rowStart + columns);
    const clusters = rowRoots.map(root => {
      const ordered: Array<{ id: string; depth: number }> = [];
      const visit = (id: string, depth: number) => {
        if (!visible.has(id)) return;
        ordered.push({ id, depth });
        (hierarchy.children[id] || []).forEach(child => visit(child, depth + 1));
      };
      visit(root, 0);
      return ordered;
    });
    const rowHeight = Math.max(...clusters.map(cluster => cluster.length), 1) * nodeStep;
    clusters.forEach((cluster, column) => {
      cluster.forEach(({ id, depth }, index) => {
        positions.set(id, {
          x: 36 + column * columnWidth + Math.min(depth, 3) * 18,
          y: rowY + index * nodeStep,
        });
      });
    });
    rowY += rowHeight + rowGap;
  }

  return nodes.map(node => ({
    ...(byId.get(node.id) || node),
    position: positions.get(node.id) || node.position,
  }));
}

function highestSeverity(id: string, sections: Record<string, ContractSection>, descendants: string[]): string | undefined {
  return [id, ...descendants].reduce<string | undefined>((highest, sectionId) => {
    const next = sections[sectionId]?.riskInfo?.severity;
    return next && severityRank[next] > (severityRank[highest || ''] || 0) ? next : highest;
  }, undefined);
}

export const ContractGraph: React.FC<GraphProps> = ({ data, onNodeClick, onEdgeSelect, selectedId }) => {
  const sections = useMemo(() => data.sectionsMap || {}, [data.sectionsMap]);
  const hierarchy = useMemo(() => buildHierarchy(sections), [sections]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [connectedOnly, setConnectedOnly] = useState(false);
  const [riskOnly, setRiskOnly] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [selectedLinksOnly, setSelectedLinksOnly] = useState(false);
  const [relationFilter, setRelationFilter] = useState('ALL');
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [flow, setFlow] = useState<ReactFlowInstance | null>(null);

  const relations = useMemo(
    () => [...new Set((data.edges || []).flatMap(edge => edge.relations))].sort(),
    [data.edges],
  );

  const effectiveExpanded = useMemo(
    () => new Set([...expanded, ...getAncestors(selectedId, hierarchy)]),
    [expanded, hierarchy, selectedId],
  );

  const toggleNode = useCallback((id: string) => {
    if (!(hierarchy.children[id] || []).length) return;
    onEdgeSelect(null);
    setExpanded(current => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
        (hierarchy.descendants[id] || []).forEach(descendant => next.delete(descendant));
        if (selectedId && hierarchy.descendants[id]?.includes(selectedId)) onNodeClick(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, [hierarchy, onEdgeSelect, onNodeClick, selectedId]);

  const graph = useMemo(() => {
    const allVisible = visibleNodeIds(hierarchy, effectiveExpanded);
    const aggregated = aggregateVisibleEdges(data.edges || [], allVisible, hierarchy, relationFilter);
    const relationshipEdges = selectedLinksOnly && selectedId
      ? aggregated.edges.filter(edge => edge.source === selectedId || edge.target === selectedId)
      : aggregated.edges;
    const connected = new Set(relationshipEdges.flatMap(edge => [edge.source, edge.target]));
    const focused = focusMode ? focusNeighborhood(selectedId, allVisible, aggregated.edges, hierarchy) : new Set(allVisible);
    const keptIds = allVisible.filter(id => {
      const severity = highestSeverity(id, sections, hierarchy.descendants[id] || []);
      return (!connectedOnly || connected.has(id)) && (!riskOnly || !!severity);
    });
    const kept = new Set(keptIds);
    const visibleEdges = relationshipEdges.filter(edge => kept.has(edge.source) && kept.has(edge.target));
    const nodes: Node<ClauseNodeData>[] = keptIds.map(id => {
      const section = sections[id];
      const childCount = (hierarchy.descendants[id] || []).length;
      return {
        id,
        type: 'clause',
        position: { x: 0, y: 0 },
        data: {
          identifier: section.canonical_id || section.id,
          title: section.title,
          childCount,
          externalCount: aggregated.externalCounts[id] || 0,
          internalCount: aggregated.internalCounts[id] || 0,
          severity: highestSeverity(id, sections, hierarchy.descendants[id] || []),
          expanded: effectiveExpanded.has(id),
          hasChildren: !!hierarchy.children[id]?.length,
          selected: id === selectedId,
          dimmed: focusMode && !focused.has(id),
          onToggle: toggleNode,
        },
        selectable: true,
        draggable: false,
      };
    });
    const laidOutNodes = layout(nodes, hierarchy);
    const nodePositions = new Map(laidOutNodes.map(node => [node.id, node.position]));
    const edges: Edge[] = visibleEdges.map(edge => {
      const selected = edge.id === selectedEdgeId;
      const highlighted = selected || (!!selectedId && (edge.source === selectedId || edge.target === selectedId));
      const dimmed = focusMode && (!focused.has(edge.source) || !focused.has(edge.target));
      const sourceX = nodePositions.get(edge.source)?.x || 0;
      const targetX = nodePositions.get(edge.target)?.x || 0;
      const flowsRight = sourceX <= targetX;
      return {
        id: edge.id,
        type: 'clause',
        source: edge.source,
        target: edge.target,
        sourceHandle: flowsRight ? 'source-right' : 'source-left',
        targetHandle: flowsRight ? 'target-left' : 'target-right',
        selected,
        markerEnd: { type: MarkerType.ArrowClosed, color: highlighted ? '#0284c7' : '#94a3b8', width: 15, height: 15 },
        data: {
          count: edge.count,
          relations: edge.relations,
          labelDetails: edge.labelDetails,
          sources: edge.sources,
          rawEdgeIds: edge.rawEdgeIds,
          evidenceQuotes: edge.evidenceQuotes,
          highlighted,
          dimmed,
        },
        selectable: true,
        focusable: true,
      };
    });
    return { nodes: laidOutNodes, edges, visibleEdges };
  }, [connectedOnly, data.edges, effectiveExpanded, focusMode, hierarchy, relationFilter, riskOnly, sections, selectedEdgeId, selectedId, selectedLinksOnly, toggleNode]);

  const expandSelected = () => {
    if (!selectedId) return;
    setExpanded(current => new Set([...current, ...getAncestors(selectedId, hierarchy), selectedId]));
  };

  const selectedRelationships = useMemo(() => {
    if (!selectedId) return [];
    return graph.visibleEdges.filter(edge => edge.source === selectedId || edge.target === selectedId);
  }, [graph.visibleEdges, selectedId]);

  return (
    <div className="relative h-full w-full bg-slate-50">
      <div className="absolute left-3 top-3 z-10 flex max-w-[calc(100%-1.5rem)] flex-wrap items-center gap-2 border border-slate-200 bg-white p-2 shadow-sm">
        <span className="mr-1 text-xs font-semibold text-slate-700">Clause map</span>
        <button title="Expand selected section" onClick={expandSelected} disabled={!selectedId} className="p-1.5 text-slate-600 hover:bg-slate-100 disabled:opacity-30"><LocateFixed size={16} /></button>
        <button title="Collapse all sections" onClick={() => setExpanded(new Set())} className="p-1.5 text-slate-600 hover:bg-slate-100"><Minimize2 size={15} /></button>
        <button title="Fit contract map" onClick={() => flow?.fitView({ padding: 0.18, duration: 300 })} className="p-1.5 text-slate-600 hover:bg-slate-100"><Crosshair size={15} /></button>
        <button title="Focus selected clause neighborhood" onClick={() => setFocusMode(value => !value)} disabled={!selectedId} className={`p-1.5 hover:bg-slate-100 disabled:opacity-30 ${focusMode ? 'bg-sky-50 text-sky-700' : 'text-slate-600'}`}><Focus size={15} /></button>
        <button
          title="Show only relationships connected to the selected clause"
          onClick={() => setSelectedLinksOnly(value => !value)}
          disabled={!selectedId}
          className={`inline-flex items-center gap-1 border-l border-slate-200 px-2 py-1 text-xs hover:bg-slate-100 disabled:opacity-30 ${selectedLinksOnly ? 'bg-sky-50 text-sky-700' : 'text-slate-600'}`}
        >
          <Link2 size={13} /> Selected links
        </button>
        <label className="flex items-center gap-1 pl-1 text-xs text-slate-600"><input type="checkbox" checked={connectedOnly} onChange={event => setConnectedOnly(event.target.checked)} /> Linked</label>
        <label className="flex items-center gap-1 text-xs text-slate-600"><input type="checkbox" checked={riskOnly} onChange={event => setRiskOnly(event.target.checked)} /> Risky</label>
        <Filter size={14} className="text-slate-400" />
        <select value={relationFilter} onChange={event => setRelationFilter(event.target.value)} className="h-7 max-w-44 border border-slate-200 bg-white px-1 text-xs">
          <option value="ALL">All relationships</option>
          {relations.map(value => <option key={value} value={value}>{value}</option>)}
        </select>
      </div>

      <ReactFlow
        nodes={graph.nodes}
        edges={graph.edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onInit={setFlow}
        onNodeClick={(_, node) => {
          setSelectedEdgeId(null);
          onEdgeSelect(null);
          onNodeClick(node.id);
        }}
        onNodeDoubleClick={(_, node) => toggleNode(node.id)}
        onEdgeClick={(_, edge) => {
          const selectedEdge = graph.visibleEdges.find(item => item.id === edge.id);
          setSelectedEdgeId(edge.id);
          onEdgeSelect(selectedEdge ? {
            sourceId: selectedEdge.source,
            targetId: selectedEdge.target,
            count: selectedEdge.count,
            relations: selectedEdge.relations,
            labelDetails: selectedEdge.labelDetails,
            sources: selectedEdge.sources,
            rawEdgeIds: selectedEdge.rawEdgeIds,
            evidenceQuotes: selectedEdge.evidenceQuotes,
          } : null);
          onNodeClick(edge.source);
        }}
        onPaneClick={() => {
          setFocusMode(false);
          setSelectedEdgeId(null);
          onEdgeSelect(null);
        }}
        nodesDraggable={false}
        fitView
        fitViewOptions={{ padding: 0.42, maxZoom: 0.55 }}
        minZoom={0.18}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e2e8f0" gap={20} size={1} />
        <Controls className="border border-slate-200 bg-white shadow-sm" showInteractive={false} />
      </ReactFlow>

      {selectedId && (
        <aside className="absolute bottom-3 right-3 z-10 w-[min(22rem,calc(100%-1.5rem))] border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center gap-2 border-b border-slate-100 px-3 py-2 text-xs font-semibold text-slate-700">
            <Link2 size={14} className="text-sky-700" />
            Contextual links ({selectedRelationships.length})
          </div>
          <div className="max-h-44 overflow-y-auto divide-y divide-slate-100">
            {selectedRelationships.map(edge => {
              const otherId = edge.source === selectedId ? edge.target : edge.source;
              const direction = edge.source === selectedId ? 'to' : 'from';
              return (
                <button
                  key={edge.id}
                  type="button"
                  onClick={() => {
                    setSelectedEdgeId(edge.id);
                    onEdgeSelect({
                      sourceId: edge.source, targetId: edge.target, count: edge.count,
                      relations: edge.relations, labelDetails: edge.labelDetails, sources: edge.sources,
                      rawEdgeIds: edge.rawEdgeIds, evidenceQuotes: edge.evidenceQuotes,
                    });
                  }}
                  className="block w-full px-3 py-2 text-left hover:bg-sky-50"
                >
                  <span className="block truncate text-[10px] font-medium uppercase tracking-wide text-slate-400">{direction} {sections[otherId]?.canonical_id || otherId}</span>
                  <span className="block text-xs font-medium leading-4 text-slate-700">{edge.relations.slice(0, 2).join(' · ')}{edge.relations.length > 2 ? ` +${edge.relations.length - 2}` : ''}</span>
                </button>
              );
            })}
            {!selectedRelationships.length && <p className="px-3 py-3 text-xs text-slate-500">No visible cross-section links for this selection.</p>}
          </div>
        </aside>
      )}

      <div className="absolute bottom-3 left-3 z-10 border border-slate-200 bg-white px-3 py-2 text-[11px] text-slate-500 shadow-sm">
        Double-click a section to expand it. Select a clause to browse its contextual links without covering the map.
      </div>
    </div>
  );
};

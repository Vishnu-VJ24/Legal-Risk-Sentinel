import React, { useMemo, useState } from 'react';
import type { ContractSection } from '../api/types';
import type { SelectedGraphEdge } from '../context/PipelineContext';
import { usePipeline } from '../context/PipelineContext';
import { buildHierarchy, getAncestors } from '../lib/clauseGraph';
import { cn, getSeverityBadgeStyles, getSeverityCardStyles } from '../lib/utils';
import {
  AlertTriangle,
  BarChart3,
  ChevronDown,
  ChevronRight,
  FileText,
  Link,
  MousePointerClick,
  Network,
} from 'lucide-react';
import { Badge } from './ui/badge';
import { Card } from './ui/card';
import { ScrollArea } from './ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';

type Hierarchy = ReturnType<typeof buildHierarchy>;

const ClauseBreadcrumbs: React.FC<{
  ids: string[];
  sections: Record<string, ContractSection>;
  onSelect: (id: string) => void;
}> = ({ ids, sections, onSelect }) => (
  <nav aria-label="Clause hierarchy" className="mt-2 flex flex-wrap items-center gap-1 text-[10px] text-slate-500">
    {ids.map((id, index) => (
      <React.Fragment key={id}>
        {index > 0 && <span className="text-slate-300">/</span>}
        <button
          type="button"
          onClick={() => onSelect(id)}
          className="max-w-28 truncate hover:text-sky-700"
          title={sections[id]?.title || id}
        >
          {sections[id]?.canonical_id || id}
        </button>
      </React.Fragment>
    ))}
  </nav>
);

const SelectedEdgeDetails: React.FC<{ edge: SelectedGraphEdge | null }> = ({ edge }) => {
  if (!edge) return null;
  return (
    <Card className="border-sky-200 bg-sky-50/50 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-sky-700">Selected relationship</p>
      <p className="mt-1 font-mono text-xs text-slate-700">{edge.sourceId} -&gt; {edge.targetId}</p>
      <p className="mt-1 text-xs text-slate-600">
        {edge.count} underlying reference{edge.count === 1 ? '' : 's'}
      </p>
      <div className="mt-2 space-y-1.5">
        {edge.labelDetails.map(detail => (
          <div key={detail.label} className="flex items-center justify-between gap-2 text-xs">
            <span className="font-medium text-slate-700">{detail.label}</span>
            <Badge variant="outline" className="shrink-0 text-[9px]">
              {detail.source === 'fallback' ? 'fallback' : detail.source}
            </Badge>
          </div>
        ))}
      </div>
      {edge.sources.length > 0 && (
        <p className="mt-2 text-[11px] text-slate-500">
          Sources: {edge.sources.join(', ')}
        </p>
      )}
      <p className="mt-1 text-[11px] text-slate-500">Artifact IDs: {edge.rawEdgeIds.join(', ')}</p>
      {edge.evidenceQuotes.map((quote, index) => (
        <p key={index} className="mt-2 border-l-2 border-sky-300 pl-2 text-xs italic leading-relaxed text-slate-600">
          "{quote}"
        </p>
      ))}
    </Card>
  );
};

const ClauseOutline: React.FC<{
  parentId: string;
  sections: Record<string, ContractSection>;
  hierarchy: Hierarchy;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
  depth?: number;
}> = ({ parentId, sections, hierarchy, expandedIds, onToggle, onSelect, depth = 0 }) => {
  const childIds = hierarchy.children[parentId] || [];
  if (childIds.length === 0) return null;
  return (
    <div className={cn('space-y-1.5', depth > 0 && 'mt-2 border-l border-slate-200 pl-3')}>
      {childIds.map(childId => {
        const child = sections[childId];
        if (!child) return null;
        const expanded = expandedIds.has(childId);
        const hasChildren = (hierarchy.children[childId] || []).length > 0;
        return (
          <div key={childId} className="border border-slate-200 bg-white">
            <div className="flex items-start gap-2 p-2.5">
              <button
                type="button"
                aria-label={`${expanded ? 'Collapse' : 'Expand'} ${child.canonical_id || child.id}`}
                onClick={() => onToggle(childId)}
                className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
              >
                {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>
              <button type="button" onClick={() => onSelect(childId)} className="min-w-0 flex-1 text-left">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-mono text-xs font-semibold text-sky-800">{child.canonical_id || child.id}</span>
                  {child.riskInfo && (
                    <Badge className={cn('shrink-0 text-[9px] font-semibold', getSeverityBadgeStyles(child.riskInfo.severity))}>
                      {child.riskInfo.severity}
                    </Badge>
                  )}
                </div>
                <p className="mt-1 line-clamp-2 text-xs font-medium leading-4 text-slate-700">{child.title || child.id}</p>
              </button>
            </div>
            {expanded && (
              <div className="border-t border-slate-100 bg-slate-50/70 p-3">
                <p className="max-h-40 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-slate-600">{child.content}</p>
                {hasChildren && (
                  <ClauseOutline
                    parentId={childId}
                    sections={sections}
                    hierarchy={hierarchy}
                    expandedIds={expandedIds}
                    onToggle={onToggle}
                    onSelect={onSelect}
                    depth={depth + 1}
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

const InspectorHeader: React.FC<{
  section: ContractSection;
  breadcrumbIds: string[];
  sections: Record<string, ContractSection>;
  onSelect: (id: string) => void;
}> = ({ section, breadcrumbIds, sections, onSelect }) => (
  <div className="shrink-0 border-b bg-muted/20 p-4">
    <div className="mb-1.5 flex items-center justify-between">
      <Badge variant="outline" className="bg-background font-mono text-xs shadow-sm">{section.id}</Badge>
      {section.riskInfo && (
        <Badge className={cn('text-xs font-bold shadow-sm', getSeverityBadgeStyles(section.riskInfo.severity))}>
          <AlertTriangle size={11} className="mr-1" />
          {section.riskInfo.severity}
        </Badge>
      )}
    </div>
    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Clause Details</p>
    <h2 className="mt-1 line-clamp-2 text-base font-semibold leading-snug">{section.title || section.id}</h2>
    <ClauseBreadcrumbs ids={breadcrumbIds} sections={sections} onSelect={onSelect} />
  </div>
);

const RelationshipList: React.FC<{
  title: string;
  direction: 'outbound' | 'inbound';
  links: ContractSection['linkedTo'] | ContractSection['linkedFrom'];
  sections: Record<string, ContractSection>;
  onSelect: (id: string) => void;
}> = ({ title, direction, links, sections, onSelect }) => {
  const Icon = direction === 'outbound' ? Link : Network;
  return (
    <div className={cn('space-y-2', direction === 'inbound' && 'border-t pt-3')}>
      <h3 className={cn('flex items-center text-xs font-semibold uppercase tracking-wide', direction === 'outbound' ? 'text-blue-700' : 'text-purple-700')}>
        <Icon size={12} className="mr-1.5" /> {title}
      </h3>
      <div className="space-y-1.5">
        {links.map((link, index) => {
          const id = 'targetId' in link ? link.targetId : link.sourceId;
          return (
            <button
              key={`${id}:${index}`}
              className="w-full rounded-xl border bg-background p-2.5 text-left text-sm transition-colors hover:bg-accent"
              onClick={() => onSelect(id)}
            >
              <div className="mb-0.5 flex items-center justify-between">
                <span className="font-mono text-xs font-semibold">{id}</span>
                <Badge variant="outline" className="text-[9px]">{link.relation}</Badge>
              </div>
              <p className="line-clamp-1 text-xs text-muted-foreground">{sections[id]?.title || 'Unknown Section'}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
};

const InspectorTabs: React.FC<{
  section: ContractSection;
  sections: Record<string, ContractSection>;
  hierarchy: Hierarchy;
  selectedSectionId: string;
  selectedEdge: SelectedGraphEdge | null;
  expandedIds: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (id: string) => void;
  desktop?: boolean;
}> = ({ section, sections, hierarchy, selectedSectionId, selectedEdge, expandedIds, onToggle, onSelect, desktop }) => {
  const childCount = (hierarchy.children[selectedSectionId] || []).length;
  const activeEdge = selectedEdge
    && (selectedEdge.sourceId === selectedSectionId || selectedEdge.targetId === selectedSectionId)
    ? selectedEdge
    : null;
  const contents = (
    <>
      <TabsContent value="details" className="mt-0 space-y-5 p-4">
        {section.riskInfo && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-destructive">Risk Analysis</h3>
            <Card className={cn('p-4 shadow-sm', getSeverityCardStyles(section.riskInfo.severity))}>
              <p className="mb-1 font-bold uppercase tracking-wide">{section.riskInfo.risk_type}</p>
              <p className="text-xs leading-relaxed opacity-90">{section.riskInfo.rationale}</p>
            </Card>
          </div>
        )}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide">Clause Text</h3>
          <div className={cn('overflow-auto rounded-2xl border bg-muted/20 p-3 text-xs leading-relaxed whitespace-pre-wrap text-muted-foreground', desktop && 'max-h-[300px]')}>
            {section.content}
          </div>
        </div>
        {childCount > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wide">Subclauses ({childCount})</h3>
            <ClauseOutline parentId={selectedSectionId} sections={sections} hierarchy={hierarchy} expandedIds={expandedIds} onToggle={onToggle} onSelect={onSelect} />
          </div>
        )}
      </TabsContent>
      <TabsContent value="context" className="mt-0 space-y-4 p-4">
        <SelectedEdgeDetails edge={activeEdge} />
        {section.linkedTo.length === 0 && section.linkedFrom.length === 0 && (
          <p className="text-sm italic text-muted-foreground">No linked clauses found for this section.</p>
        )}
        {section.linkedTo.length > 0 && (
          <RelationshipList title="Outbound References" direction="outbound" links={section.linkedTo} sections={sections} onSelect={onSelect} />
        )}
        {section.linkedFrom.length > 0 && (
          <RelationshipList title="Referenced By" direction="inbound" links={section.linkedFrom} sections={sections} onSelect={onSelect} />
        )}
      </TabsContent>
      <TabsContent value="evidence" className="mt-0 space-y-4 p-4">
        {!section.riskInfo?.evidence?.length ? (
          <p className="text-sm italic text-muted-foreground">No specific risk evidence extracted for this section.</p>
        ) : (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide">Supporting Quotes</h3>
            {section.riskInfo.evidence.map((evidence, index) => (
              <Card key={index} className="border-l-4 border-l-amber-400 bg-amber-50/20 p-3">
                <p className="text-xs italic leading-relaxed text-amber-900/70">"{evidence}"</p>
              </Card>
            ))}
          </div>
        )}
      </TabsContent>
    </>
  );
  return (
    <Tabs defaultValue="details" className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b px-3 pt-2">
        <TabsList className="grid h-8 w-full grid-cols-3 bg-muted/50">
          <TabsTrigger value="details" className="text-xs">Details</TabsTrigger>
          <TabsTrigger value="context" className="text-xs">Context</TabsTrigger>
          <TabsTrigger value="evidence" className="text-xs">Evidence</TabsTrigger>
        </TabsList>
      </div>
      {desktop ? <ScrollArea className="flex-1">{contents}</ScrollArea> : <div className="max-h-[420px] overflow-y-auto">{contents}</div>}
    </Tabs>
  );
};

const MobileInspectorEmptyState = () => (
  <div className="rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm lg:hidden">
    <div className="flex items-start gap-4">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted/40">
        <MousePointerClick size={22} className="text-muted-foreground/30" />
      </div>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Clause Details</p>
        <h3 className="mt-1 text-base font-semibold text-slate-900">Tap a clause to inspect it</h3>
        <p className="mt-1 text-sm leading-relaxed text-slate-500">Select a node or priority clause to see risk details, evidence, and linked references.</p>
      </div>
    </div>
  </div>
);

export const RightInspector: React.FC = () => {
  const { data, selectedSectionId, selectedEdge, setSelectedSectionId, stage } = usePipeline();
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const hierarchy = useMemo(() => buildHierarchy(data?.sectionsMap || {}), [data?.sectionsMap]);
  const toggle = (id: string) => setExpandedIds(current => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });

  if (!selectedSectionId || !data?.sectionsMap?.[selectedSectionId]) {
    return (
      <>
        <MobileInspectorEmptyState />
        <div className="hidden h-full w-full min-w-0 flex-col border-l bg-card/50 lg:flex">
          <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
            <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-muted/40">
              <MousePointerClick size={28} className="text-muted-foreground/30" />
            </div>
            <h3 className="mb-1.5 font-semibold text-foreground">Clause Details</h3>
            <p className="max-w-[220px] text-sm leading-relaxed text-muted-foreground">Click a node or priority clause to inspect its details, links, and evidence.</p>
            {data?.meta && ['SECTIONS_BUILT', 'GRAPH_READY', 'RISKS_ANALYZED', 'REPORT_READY'].includes(stage) && (
              <div className="mt-8 w-full space-y-3">
                <div className="h-px w-full bg-border" />
                <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">Quick Overview</p>
                <div className="grid grid-cols-2 gap-2 text-left">
                  <Card className="bg-background p-2.5">
                    <p className="flex items-center text-[10px] text-muted-foreground"><FileText size={10} className="mr-1" />Clauses</p>
                    <p className="text-lg font-bold">{data.meta.totalSections}</p>
                  </Card>
                  <Card className="bg-background p-2.5">
                    <p className="flex items-center text-[10px] text-muted-foreground"><BarChart3 size={10} className="mr-1" />Flagged</p>
                    <p className="text-lg font-bold">{data.meta.flaggedSections}</p>
                  </Card>
                </div>
              </div>
            )}
          </div>
        </div>
      </>
    );
  }

  const section = data.sectionsMap[selectedSectionId];
  const breadcrumbIds = [...getAncestors(selectedSectionId, hierarchy), selectedSectionId];
  const shared = {
    section,
    sections: data.sectionsMap,
    hierarchy,
    selectedSectionId,
    selectedEdge,
    expandedIds,
    onToggle: toggle,
    onSelect: setSelectedSectionId,
  };
  return (
    <>
      <div className="rounded-3xl border border-slate-200 bg-white/95 shadow-sm lg:hidden">
        <InspectorHeader section={section} breadcrumbIds={breadcrumbIds} sections={data.sectionsMap} onSelect={setSelectedSectionId} />
        <InspectorTabs {...shared} />
      </div>
      <div className="z-20 hidden h-full w-full min-w-0 flex-col border-l bg-card shadow-[-4px_0_15px_-4px_rgba(0,0,0,0.04)] lg:flex">
        <InspectorHeader section={section} breadcrumbIds={breadcrumbIds} sections={data.sectionsMap} onSelect={setSelectedSectionId} />
        <InspectorTabs {...shared} desktop />
      </div>
    </>
  );
};

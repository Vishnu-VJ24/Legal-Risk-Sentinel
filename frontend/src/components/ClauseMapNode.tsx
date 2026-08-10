import React from 'react';
import { ChevronDown, ChevronRight, Link2, ShieldAlert } from 'lucide-react';
import { Handle, NodeProps, Position } from '@xyflow/react';
import { cn } from '../lib/utils';

export interface ClauseNodeData extends Record<string, unknown> {
  identifier: string;
  title: string;
  childCount: number;
  externalCount: number;
  internalCount: number;
  severity?: string;
  expanded: boolean;
  hasChildren: boolean;
  selected: boolean;
  dimmed: boolean;
  onToggle: (id: string) => void;
}

const severityBorder: Record<string, string> = {
  CRITICAL: 'border-red-500',
  HIGH: 'border-orange-500',
  MEDIUM: 'border-amber-400',
  LOW: 'border-slate-400',
};

export const ClauseMapNode: React.FC<NodeProps> = ({ id, data }) => {
  const node = data as ClauseNodeData;
  return (
    <div className={cn(
      'relative w-[250px] border-2 bg-white px-3 py-2.5 text-slate-900 shadow-sm transition-[opacity,box-shadow,border-color] duration-150',
      severityBorder[node.severity || ''] || 'border-slate-200',
      node.selected && 'shadow-[0_0_0_3px_rgba(14,165,233,0.22),0_8px_18px_rgba(15,23,42,0.1)]',
      node.dimmed && 'opacity-20',
    )}>
      <Handle id="target-left" type="target" position={Position.Left} className="!h-2 !w-2 !border-white !bg-slate-400" />
      <Handle id="target-right" type="target" position={Position.Right} className="!h-2 !w-2 !border-white !bg-slate-400" />
      <Handle id="source-left" type="source" position={Position.Left} className="!h-2 !w-2 !border-white !bg-slate-400" />
      <Handle id="source-right" type="source" position={Position.Right} className="!h-2 !w-2 !border-white !bg-slate-400" />
      <div className="flex items-start gap-2">
        {node.hasChildren ? (
          <button
            type="button"
            title={node.expanded ? 'Collapse section' : 'Expand section'}
            aria-label={node.expanded ? 'Collapse section' : 'Expand section'}
            onClick={(event) => {
              event.stopPropagation();
              node.onToggle(id);
            }}
            className="nodrag mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100"
          >
            {node.expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        ) : <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-slate-300" />}
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-mono text-[11px] font-semibold text-sky-800">{node.identifier}</span>
            {node.severity && <ShieldAlert size={13} className="shrink-0 text-orange-600" />}
          </div>
          <p className="mt-1 line-clamp-2 text-xs font-semibold leading-4">{node.title || node.identifier}</p>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-slate-100 pt-2 text-[10px] font-medium text-slate-500">
        {node.childCount > 0 && <span>{node.childCount} clauses</span>}
        <span className="inline-flex items-center gap-1"><Link2 size={10} />{node.externalCount} external</span>
        {node.internalCount > 0 && <span>{node.internalCount} internal</span>}
      </div>
    </div>
  );
};

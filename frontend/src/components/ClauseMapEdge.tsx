import React, { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, EdgeProps, getSmoothStepPath } from '@xyflow/react';

interface ClauseEdgeData extends Record<string, unknown> {
  count: number;
  relations: string[];
  highlighted: boolean;
  dimmed: boolean;
}

export const ClauseMapEdge: React.FC<EdgeProps> = ({
  id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, selected, data,
}) => {
  const [hovered, setHovered] = useState(false);
  const edge = data as ClauseEdgeData;
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, borderRadius: 10, offset: 30,
  });
  const emphasized = selected || hovered || edge.highlighted;
  // A selected node can have many links. Keep its paths highlighted, but leave
  // labels to the hovered or explicitly selected edge so chips never stack.
  const showLabel = (selected || hovered) && !edge.dimmed;
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        interactionWidth={22}
        style={{
          stroke: emphasized ? '#0284c7' : '#94a3b8',
          strokeWidth: emphasized ? Math.min(4, 1.8 + edge.count * 0.35) : Math.min(3, 1 + edge.count * 0.25),
          opacity: edge.dimmed ? 0.08 : 0.82,
        }}
      />
      <path
        d={path}
        fill="none"
        stroke="transparent"
        strokeWidth={22}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      />
      {showLabel && (
        <EdgeLabelRenderer>
          <div
            className="pointer-events-none absolute max-w-64 border border-sky-200 bg-white px-2 py-1 text-[10px] font-medium leading-4 text-slate-700 shadow-sm"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)` }}
          >
            <span className="font-semibold text-sky-700">{edge.count} link{edge.count === 1 ? '' : 's'}</span>
            <span className="mx-1 text-slate-300">|</span>
            {edge.relations.slice(0, 2).join(', ')}
            {edge.relations.length > 2 && (
              <span className="ml-1 text-slate-400">+{edge.relations.length - 2}</span>
            )}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};

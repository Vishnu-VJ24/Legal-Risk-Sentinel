import { motion } from 'framer-motion';
import { Copy, Flag } from 'lucide-react';
import { useState } from 'react';
import type { ClauseResult } from '../../types/contracts';
import { cn } from '../../utils/cn';
import { riskLevelStyles } from '../../utils/contracts';

interface ClauseCardProps {
  clause: ClauseResult;
  highlighted?: boolean;
}

const axes: Array<keyof ClauseResult['risk_axes']> = ['liability', 'indemnity', 'ip_rights', 'termination'];

export const ClauseCard = ({ clause, highlighted }: ClauseCardProps) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.article
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      id={clause.id}
      className={cn('rounded-[24px] border border-border bg-background/70 p-5', highlighted && 'border-primary/60 shadow-glow')}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span className={cn('rounded-full border px-3 py-1 text-xs font-semibold uppercase', riskLevelStyles[clause.risk_level])}>
          {clause.type}
        </span>
        <span className="rounded-full bg-surface px-3 py-1 text-sm font-semibold text-text-secondary">
          Risk {clause.risk_score.toFixed(1)}/10
        </span>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface">
        <div className="h-full rounded-full bg-gradient-to-r from-secondary to-primary" style={{ width: `${clause.risk_score * 10}%` }} />
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {axes.map((axis) => (
          <div key={axis}>
            <div className="mb-1 flex items-center justify-between text-xs uppercase tracking-[0.2em] text-text-secondary">
              <span>{axis.replace('_', ' ')}</span>
              <span>{clause.risk_axes[axis]}/10</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface">
              <div className="h-full rounded-full bg-primary/80" style={{ width: `${clause.risk_axes[axis] * 10}%` }} />
            </div>
          </div>
        ))}
      </div>
      <p className="mt-4 text-sm leading-7 text-text-secondary">
        {expanded ? clause.text : `${clause.text.slice(0, 180)}${clause.text.length > 180 ? '…' : ''}`}
      </p>
      {clause.text.length > 180 ? (
        <button type="button" onClick={() => setExpanded((current) => !current)} className="mt-2 text-sm text-primary">
          {expanded ? 'Collapse clause' : 'Expand clause'}
        </button>
      ) : null}
      <div className="mt-4 rounded-2xl border border-border bg-surface/60 p-4">
        <p className="text-xs uppercase tracking-[0.2em] text-secondary">AI Explanation</p>
        <p className="mt-2 text-sm leading-7 text-text-secondary">{clause.explanation}</p>
      </div>
      {clause.renegotiation_suggestion ? (
        <div className="mt-4 rounded-2xl border border-primary/20 bg-primary/10 p-4">
          <p className="text-xs uppercase tracking-[0.2em] text-primary">Renegotiation Suggestion</p>
          <p className="mt-2 text-sm leading-7">{clause.renegotiation_suggestion}</p>
        </div>
      ) : null}
      <div className="mt-5 flex flex-wrap gap-3">
        <button type="button" onClick={() => navigator.clipboard.writeText(clause.text)} className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm">
          <Copy className="h-4 w-4" />
          Copy clause
        </button>
        <button type="button" className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm">
          <Flag className="h-4 w-4" />
          Flag for review
        </button>
      </div>
    </motion.article>
  );
};

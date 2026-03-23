import { motion } from 'framer-motion';
import { BrainCircuit, FileSearch, ShieldCheck, Sparkles } from 'lucide-react';
import type { PipelineStage } from '../../types/contracts';
import { cn } from '../../utils/cn';

interface PipelineProgressProps {
  progress: number;
  stage: PipelineStage;
}

const steps = [
  { key: 'parsing', label: 'Parsing', icon: FileSearch },
  { key: 'extracting', label: 'Extracting', icon: Sparkles },
  { key: 'scoring', label: 'Scoring', icon: ShieldCheck },
  { key: 'explaining', label: 'Explaining', icon: BrainCircuit },
] as const;

export const PipelineProgress = ({ progress, stage }: PipelineProgressProps) => {
  const activeIndex = steps.findIndex((step) => step.key === stage);

  return (
    <div className="rounded-[28px] border border-border bg-surface/85 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-secondary">Pipeline</p>
          <h2 className="mt-2 text-2xl font-semibold">Contract analysis in progress</h2>
        </div>
        <span className="text-2xl font-semibold text-primary">{progress}%</span>
      </div>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-background">
        <motion.div className="h-full rounded-full bg-gradient-to-r from-primary to-secondary" animate={{ width: `${progress}%` }} />
      </div>
      <motion.div
        initial="hidden"
        animate="visible"
        variants={{ hidden: {}, visible: { transition: { staggerChildren: 0.12 } } }}
        className="mt-6 grid gap-4 md:grid-cols-4"
      >
        {steps.map((step, index) => {
          const active = stage === 'done' || activeIndex >= index;
          return (
            <motion.div
              key={step.key}
              variants={{ hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0 } }}
              className={cn('rounded-2xl border border-border p-4', active && 'border-primary/40 bg-primary/10')}
            >
              <step.icon className={cn('h-6 w-6 text-text-secondary', active && 'text-primary')} />
              <p className="mt-3 font-medium">{step.label}</p>
              <p className="mt-1 text-sm text-text-secondary">
                {active ? 'Stage complete or running' : 'Queued'}
              </p>
            </motion.div>
          );
        })}
      </motion.div>
    </div>
  );
};

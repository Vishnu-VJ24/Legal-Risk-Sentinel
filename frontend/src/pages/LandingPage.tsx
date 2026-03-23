import { motion } from 'framer-motion';
import { BrainCircuit, FileSearch, ShieldAlert } from 'lucide-react';
import { HeroSectionDark } from '../components/ui/HeroSectionDark';
import { Vortex } from '../components/ui/Vortex';

const features = [
  {
    title: 'Clause Extraction',
    description: 'Identify key obligations, carve-outs, and hidden clauses with structure-aware parsing.',
    icon: FileSearch,
  },
  {
    title: 'Risk Scoring',
    description: 'Score legal exposure across indemnity, liability, IP, termination, and more.',
    icon: ShieldAlert,
  },
  {
    title: 'AI Explanations',
    description: 'Turn dense legal language into plain-English rationale and renegotiation guidance.',
    icon: BrainCircuit,
  },
];

export const LandingPage = () => {
  return (
    <div className="relative flex flex-1 flex-col gap-16 overflow-hidden py-10">
      <Vortex
        particleCount={220}
        baseHue={248}
        containerClassName="pointer-events-none absolute inset-0 min-h-[140vh] opacity-100"
        className="hidden"
      />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_10%,rgba(var(--color-primary)/0.24),transparent_26%),radial-gradient(circle_at_78%_20%,rgba(var(--color-secondary)/0.18),transparent_24%),radial-gradient(circle_at_22%_24%,rgba(var(--color-primary)/0.12),transparent_18%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,rgba(10,10,15,0.25)_0%,rgba(10,10,15,0.45)_38%,rgba(10,10,15,0.72)_70%,rgba(10,10,15,0.92)_100%)]" />
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="relative z-10">
        <HeroSectionDark
          title="AI Contract Intelligence"
          subtitle={{
            regular: 'Understand Every Clause. ',
            gradient: 'Before You Sign.',
          }}
          description="LexAI combines document parsing, clause extraction, risk scoring, and explainable AI so legal review feels fast, structured, and recruiter-demo ready."
          ctaText="Start Analysis"
          ctaHref="/analyze"
          secondaryText="View Repository"
          secondaryHref="https://github.com/Vishnu-VJ24/Legal-Risk-Sentinel"
          gridOptions={{
            angle: 64,
            opacity: 0.12,
            cellSize: 64,
            lineColor: 'rgba(139, 139, 167, 0.08)',
          }}
        />
      </motion.div>

      <section className="relative z-10 grid gap-6 md:grid-cols-3">
        {features.map((feature, index) => (
          <motion.article
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * index }}
            className="rounded-3xl border border-border bg-surface/45 p-6 backdrop-blur-md"
          >
            <feature.icon className="h-10 w-10 text-primary" />
            <h2 className="mt-5 text-xl font-semibold">{feature.title}</h2>
            <p className="mt-3 text-sm leading-7 text-text-secondary">{feature.description}</p>
          </motion.article>
        ))}
      </section>
      <footer className="relative z-10 rounded-[28px] border border-border bg-surface/45 px-6 py-6 backdrop-blur-md">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <p className="text-sm text-text-secondary">
            Built with React, TypeScript, FastAPI, Tailwind CSS, TanStack Query, and production-minded AI app patterns.
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            {['React 18', 'FastAPI', 'TanStack Query', 'Tailwind v3', 'Framer Motion'].map((badge) => (
              <span key={badge} className="rounded-full border border-border px-3 py-1 text-text-secondary">
                {badge}
              </span>
            ))}
          </div>
        </div>
      </footer>
    </div>
  );
};

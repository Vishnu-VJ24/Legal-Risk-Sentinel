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
      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="relative z-10">
        <section className="relative overflow-hidden rounded-[40px] border border-white/8 bg-[#090910]">
          <Vortex
            particleCount={320}
            baseHue={304}
            containerClassName="relative min-h-[520px] sm:min-h-[600px]"
            className="flex min-h-[520px] items-center sm:min-h-[600px]"
          >
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(191,90,242,0.24),transparent_32%),radial-gradient(circle_at_75%_25%,rgba(236,72,153,0.16),transparent_28%)]" />
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
            />
          </Vortex>
        </section>
      </motion.div>

      <section className="relative z-10 grid gap-6 md:grid-cols-3">
        {features.map((feature, index) => (
          <motion.article
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * index }}
            className="rounded-3xl border border-border bg-surface/55 p-6 backdrop-blur-sm"
          >
            <feature.icon className="h-10 w-10 text-primary" />
            <h2 className="mt-5 text-xl font-semibold">{feature.title}</h2>
            <p className="mt-3 text-sm leading-7 text-text-secondary">{feature.description}</p>
          </motion.article>
        ))}
      </section>
      <footer className="relative z-10 rounded-[28px] border border-border bg-surface/55 px-6 py-6 backdrop-blur-sm">
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

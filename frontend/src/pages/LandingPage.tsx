import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, BrainCircuit, FileSearch, ShieldAlert } from 'lucide-react';
import { SectionHeading } from '../components/common/SectionHeading';

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
    <div className="flex flex-1 flex-col gap-16 py-10">
      <section className="rounded-[32px] border border-border bg-surface/80 px-6 py-14 shadow-glow sm:px-10">
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="max-w-4xl">
          <SectionHeading
            eyebrow="AI Contract Intelligence"
            title="Understand Every Clause. Before You Sign."
            description="LexAI combines document parsing, clause extraction, risk scoring, and explainable AI so legal review feels fast, structured, and recruiter-demo ready."
          />
          <div className="mt-10 flex flex-col gap-4 sm:flex-row">
            <Link
              to="/analyze"
              className="inline-flex items-center justify-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white transition hover:scale-[1.02]"
            >
              Start Analysis
              <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="https://github.com/"
              className="inline-flex items-center justify-center rounded-full border border-border px-6 py-3 text-sm font-semibold text-text-primary transition hover:border-primary/40"
            >
              View Repository
            </a>
          </div>
        </motion.div>
      </section>

      <section className="grid gap-6 md:grid-cols-3">
        {features.map((feature, index) => (
          <motion.article
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * index }}
            className="rounded-3xl border border-border bg-surface/70 p-6"
          >
            <feature.icon className="h-10 w-10 text-primary" />
            <h2 className="mt-5 text-xl font-semibold">{feature.title}</h2>
            <p className="mt-3 text-sm leading-7 text-text-secondary">{feature.description}</p>
          </motion.article>
        ))}
      </section>
      <footer className="rounded-[28px] border border-border bg-surface/70 px-6 py-6">
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

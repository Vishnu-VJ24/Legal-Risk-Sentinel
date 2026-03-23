import { motion } from 'framer-motion';
import { BrainCircuit, FileSearch, ShieldAlert } from 'lucide-react';
import { ButtonWithIcon } from '../components/ui/ButtonWithIcon';
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
    <div className="relative flex min-h-[calc(100vh-72px)] flex-1 flex-col overflow-hidden bg-[#07070c]">
      <Vortex
        particleCount={360}
        baseHue={304}
        containerClassName="absolute inset-0 min-h-full"
        className="hidden"
      />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(191,90,242,0.18),transparent_28%),radial-gradient(circle_at_75%_20%,rgba(236,72,153,0.14),transparent_26%),linear-gradient(180deg,rgba(7,7,12,0.28)_0%,rgba(7,7,12,0.72)_52%,rgba(7,7,12,0.9)_100%)]" />

      <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="relative z-10 mx-auto w-full max-w-7xl px-4 pt-12 sm:px-6 lg:px-8">
        <section className="flex min-h-[68vh] items-center justify-center">
          <div className="mx-auto flex w-full max-w-5xl flex-col items-center px-6 py-20 text-center sm:px-10 lg:px-12 lg:py-28">
            <h1 className="mt-6 max-w-4xl text-4xl font-extrabold tracking-tight text-text-primary sm:text-5xl lg:text-7xl">
              <span>Understand Every Clause. </span>
              <span className="bg-gradient-to-r from-fuchsia-400 via-violet-400 to-purple-300 bg-clip-text text-transparent">
                Before You Sign.
              </span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-text-secondary sm:text-lg">
              LexAI combines document parsing, clause extraction, risk scoring, and explainable AI so legal review
              feels fast and structured.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
              <ButtonWithIcon href="/analyze" label="Start Analysis" />
              <a
                href="https://github.com/Vishnu-VJ24/Legal-Risk-Sentinel"
                className="inline-flex items-center justify-center rounded-full border border-white/10 bg-black/25 px-8 py-4 text-sm font-semibold text-text-primary transition hover:border-primary/40 hover:bg-black/35"
              >
                View Repository
              </a>
            </div>
          </div>
        </section>
      </motion.div>

      <section className="relative z-10 mx-auto grid w-full max-w-7xl gap-6 px-4 pb-4 sm:px-6 md:grid-cols-3 lg:px-8">
        {features.map((feature, index) => (
          <motion.article
            key={feature.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 * index }}
            className="rounded-3xl border border-white/10 bg-surface/40 p-6 backdrop-blur-md"
          >
            <feature.icon className="h-10 w-10 text-primary" />
            <h2 className="mt-5 text-xl font-semibold">{feature.title}</h2>
            <p className="mt-3 text-sm leading-7 text-text-secondary">{feature.description}</p>
          </motion.article>
        ))}
      </section>
      <footer className="relative z-10 mx-auto w-full max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
        <div className="rounded-[28px] border border-white/10 bg-surface/40 px-6 py-6 backdrop-blur-md">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <p className="text-sm text-text-secondary">
            Built with React, TypeScript, FastAPI, Tailwind CSS, TanStack Query, and production-minded AI app patterns.
          </p>
          <div className="flex flex-wrap gap-2 text-xs">
            {['React 18', 'FastAPI', 'TanStack Query', 'Tailwind v3', 'Framer Motion'].map((badge) => (
              <span key={badge} className="rounded-full border border-white/10 px-3 py-1 text-text-secondary">
                {badge}
              </span>
            ))}
          </div>
        </div>
        </div>
      </footer>
    </div>
  );
};

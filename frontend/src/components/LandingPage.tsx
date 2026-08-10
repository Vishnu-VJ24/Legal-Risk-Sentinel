import React, { useRef, useState } from 'react';
import { usePipeline } from '../context/PipelineContext';
import {
  Upload,
  FileText,
  Shield,
  Activity,
  Search,
  BarChart3,
  MessageSquare,
  ArrowUpRight,
  Globe2,
  GitBranch,
  FileCheck2,
} from 'lucide-react';
import { Button } from './ui/button';
import { cn } from '../lib/utils';

const CONTRIBUTORS = [
  {
    name: 'Pranav Pant',
    role: 'Product, Backend, Deployment',
    portfolioHref: 'https://pranavds-codes.github.io/portfolio/',
    linkedinHref: 'https://www.linkedin.com/in/pranav-pant-ds/',
  },
  {
    name: 'Vishnu Jayanth Senthil Kumar',
    role: 'Frontend, Experience, Analysis',
    portfolioHref: 'https://vishnu-vj24.github.io/Vishnu-Portfolio/',
    linkedinHref: 'https://www.linkedin.com/in/vishnu--vj/',
  },
];

const FEATURES = [
  {
    icon: Search,
    title: 'Clause Relationships',
    desc: 'Trace clause references, dependencies, and structural links across the document.',
  },
  {
    icon: BarChart3,
    title: 'Risk Review',
    desc: 'Surface the most material findings with severity, rationale, and supporting evidence.',
  },
  {
    icon: MessageSquare,
    title: 'Grounded Assistant',
    desc: 'Ask follow-up questions against the extracted contract artifacts and generated review outputs.',
  },
];

const WORKFLOW = [
  {
    icon: FileText,
    label: 'Extract',
    title: 'Read the contract into structured sections',
    desc: 'The app ingests the uploaded PDF, pulls the text, and separates the contract into meaningful clause-level sections.',
  },
  {
    icon: GitBranch,
    label: 'Map',
    title: 'Build the clause relationship graph',
    desc: 'Cross-references and dependency signals are identified so the document can be explored visually instead of as a flat PDF.',
  },
  {
    icon: FileCheck2,
    label: 'Review',
    title: 'Score risks and generate an executive report',
    desc: 'The pipeline analyzes obligations, risk language, and review priority, then prepares a concise report for fast walkthroughs.',
  },
];

export const LandingPage: React.FC = () => {
  const { startAnalysis } = usePipeline();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleFileSelect = (file: File) => {
    if (file && file.type === 'application/pdf') {
      setSelectedFile(file);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileSelect(file);
  };

  const handleBeginAnalysis = () => {
    if (selectedFile) {
      startAnalysis(selectedFile);
    }
  };

  return (
    <div className="relative flex min-h-dvh w-full flex-col items-center overflow-x-hidden overflow-y-auto bg-[radial-gradient(circle_at_top_right,#38bdf8_0%,rgba(56,189,248,0.15)_16%,transparent_38%),radial-gradient(circle_at_bottom_left,rgba(15,23,42,0.95)_0%,rgba(15,23,42,0)_42%),linear-gradient(145deg,#020617,#0f172a_36%,#082f49_100%)]">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute right-[-10%] top-[-14%] h-[560px] w-[560px] rounded-full bg-cyan-300/10 blur-3xl" />
        <div className="absolute bottom-[-18%] left-[-10%] h-[500px] w-[500px] rounded-full bg-sky-500/10 blur-3xl" />
        <div className="absolute left-[42%] top-[22%] h-[260px] w-[260px] rounded-full bg-white/5 blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:64px_64px]" />
        <div className="absolute inset-x-0 top-0 h-48 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),transparent)]" />
      </div>

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 pb-10 pt-10 sm:px-6 sm:pt-14">
        <div className="grid flex-1 gap-10 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="flex min-w-0 flex-col justify-center">
            <div className="inline-flex w-fit items-center gap-2 rounded-full border border-cyan-300/20 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-100/80 backdrop-blur">
              <Shield size={13} />
              Contract Intelligence Workspace
            </div>

            <div className="mt-6 flex min-w-0 flex-col gap-4 sm:flex-row sm:items-start">
              <div className="relative mt-1 w-fit self-start">
                <div className="absolute inset-0 rounded-3xl bg-cyan-400/30 blur-xl" />
                <div className="relative rounded-3xl bg-gradient-to-br from-cyan-400 via-sky-500 to-blue-700 p-4 text-white shadow-2xl shadow-sky-950/40">
                  <Shield size={36} />
                </div>
              </div>
              <div className="min-w-0 max-w-3xl">
                <h1 className="text-4xl font-black tracking-tight text-white sm:text-6xl xl:text-7xl">Legal Sentinel</h1>
                <p className="mt-4 max-w-2xl text-lg leading-relaxed text-slate-300">
                  Legal Sentinel turns a contract PDF into a guided review workspace with structure extraction, clause mapping,
                  risk prioritization, executive reporting, and grounded Q&amp;A.
                </p>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400 sm:text-[15px]">
                  Instead of reading a long agreement as a single document, the application breaks it into sections, detects
                  clause relationships, highlights material issues, and gives you a faster way to understand obligations,
                  dependencies, and negotiation hotspots.
                </p>
              </div>
            </div>

            <div className="mt-8 grid gap-3 md:grid-cols-3">
              {FEATURES.map((feature) => (
                <div
                  key={feature.title}
                  className="rounded-2xl border border-white/10 bg-white/[0.06] p-4 shadow-[0_18px_40px_-30px_rgba(14,165,233,0.55)] backdrop-blur-sm"
                >
                  <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-2xl bg-white/[0.08] ring-1 ring-white/10">
                    <feature.icon size={18} className="text-cyan-300" />
                  </div>
                  <p className="text-sm font-semibold text-white">{feature.title}</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">{feature.desc}</p>
                </div>
              ))}
            </div>

            <div className="mt-8 rounded-[28px] border border-white/10 bg-white/[0.05] p-6 shadow-[0_24px_80px_-45px_rgba(14,165,233,0.5)] backdrop-blur-sm">
              <div className="mb-5 flex items-center gap-2 text-cyan-100">
                <Activity size={16} />
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/70">How It Works</p>
              </div>
              <div className="grid gap-4 md:grid-cols-3">
                {WORKFLOW.map((item) => (
                  <div key={item.label} className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-cyan-300/10 ring-1 ring-cyan-300/20">
                        <item.icon size={18} className="text-cyan-200" />
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-200/70">{item.label}</p>
                        <p className="text-sm font-semibold text-white">{item.title}</p>
                      </div>
                    </div>
                    <p className="mt-3 text-xs leading-relaxed text-slate-400">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="min-w-0 space-y-6 xl:pt-8">
            <div className="rounded-[32px] border border-white/12 bg-white/[0.07] p-6 shadow-[0_28px_90px_-40px_rgba(2,132,199,0.7)] backdrop-blur-xl">
              <div className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/70">Upload Contract</p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Start a guided review</h2>
                  <p className="mt-2 text-sm leading-relaxed text-slate-300">
                    Upload a PDF to extract the document, map clause dependencies, generate risk findings, and unlock the review workspace.
                  </p>
                </div>
                <div className="w-fit rounded-2xl border border-cyan-300/20 bg-cyan-300/10 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-[0.16em] text-cyan-100/90 sm:text-right">
                  Typical runtime
                  <div className="mt-1 text-lg tracking-normal text-white">Under 60s</div>
                </div>
              </div>

              <div
                className={cn(
                  'cursor-pointer rounded-[28px] border-2 border-dashed p-10 text-center transition-all duration-300',
                  'bg-slate-950/20',
                  isDragging
                    ? 'scale-[1.01] border-cyan-300 bg-cyan-400/10 shadow-lg shadow-cyan-500/15'
                    : selectedFile
                      ? 'border-cyan-300/50 bg-cyan-400/[0.08]'
                      : 'border-slate-500/60 hover:border-cyan-300/50 hover:bg-white/[0.04]'
                )}
                onClick={() => fileInputRef.current?.click()}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={handleInputChange}
                />

                {selectedFile ? (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-cyan-400/15 ring-1 ring-cyan-200/30">
                      <FileText size={30} className="text-cyan-100" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-cyan-50">{selectedFile.name}</p>
                      <p className="mt-1 text-sm text-slate-400">
                        {(selectedFile.size / 1024).toFixed(0)} KB · Ready for analysis
                      </p>
                    </div>
                    <button
                      className="text-xs text-slate-400 underline underline-offset-2 transition-colors hover:text-cyan-200"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedFile(null);
                      }}
                    >
                      Choose a different file
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-3">
                    <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/[0.06] ring-1 ring-white/10">
                      <Upload size={30} className="text-slate-300" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-100">Drop a PDF here or click to browse</p>
                      <p className="mt-1 text-sm text-slate-400">Use a contract document to launch the full review pipeline</p>
                    </div>
                  </div>
                )}
              </div>

              <Button
                size="lg"
                className={cn(
                  'mt-6 h-12 w-full rounded-2xl px-10 text-base font-semibold transition-all duration-300',
                  'bg-gradient-to-r from-cyan-400 via-sky-500 to-blue-700 text-white hover:from-cyan-300 hover:via-sky-400 hover:to-blue-600',
                  'shadow-lg shadow-sky-900/30 hover:shadow-xl hover:shadow-sky-900/35',
                  'disabled:opacity-30 disabled:shadow-none'
                )}
                disabled={!selectedFile}
                onClick={handleBeginAnalysis}
              >
                <Activity size={18} className="mr-2" />
                Begin Analysis
              </Button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-[28px] border border-white/10 bg-white/[0.05] p-6 backdrop-blur-sm">
                <div className="mb-4 flex items-center gap-2 text-cyan-100">
                  <Globe2 size={16} />
                  <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/70">Contributors</p>
                </div>
                <div className="space-y-4">
                  {CONTRIBUTORS.map((contributor) => (
                    <div key={contributor.name} className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                      <p className="text-base font-semibold text-white">{contributor.name}</p>
                      <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-400">{contributor.role}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {contributor.portfolioHref ? (
                          <a
                            href={contributor.portfolioHref}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-2 rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1.5 text-xs font-semibold text-cyan-100 transition-colors hover:bg-cyan-300/20"
                          >
                            Portfolio
                            <ArrowUpRight size={13} />
                          </a>
                        ) : (
                          <span className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-slate-400">
                            Portfolio link coming soon
                          </span>
                        )}
                        {contributor.linkedinHref ? (
                          <a
                            href={contributor.linkedinHref}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs font-semibold text-slate-200 transition-colors hover:bg-white/[0.1]"
                          >
                            LinkedIn
                            <ArrowUpRight size={13} />
                          </a>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[28px] border border-white/10 bg-white/[0.05] p-6 backdrop-blur-sm">
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-cyan-200/70">What You Get</p>
                <div className="mt-4 space-y-3">
                  <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                    <p className="text-sm font-semibold text-white">Clause graph</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">
                      A visual contract map showing how sections refer to and depend on one another.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                    <p className="text-sm font-semibold text-white">Risk-ranked review</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">
                      Priority findings with severity, rationale, and evidence to speed up manual review.
                    </p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-950/20 p-4">
                    <p className="text-sm font-semibold text-white">Executive summary + grounded chat</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">
                      A concise report for walkthroughs, plus a contract assistant that stays tied to the analyzed artifacts.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

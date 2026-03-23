import * as React from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '../../utils/cn';
import { ButtonWithIcon } from './ButtonWithIcon';

interface HeroSectionProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  subtitle?: {
    regular: string;
    gradient: string;
  };
  description?: string;
  ctaText?: string;
  ctaHref?: string;
  secondaryText?: string;
  secondaryHref?: string;
  gridOptions?: {
    angle?: number;
    cellSize?: number;
    opacity?: number;
    lineColor?: string;
  };
}

interface RetroGridProps {
  angle?: number;
  cellSize?: number;
  opacity?: number;
  lineColor?: string;
}

const RetroGrid = ({
  angle = 64,
  cellSize = 56,
  opacity = 0.45,
  lineColor = 'rgba(139, 139, 167, 0.16)',
}: RetroGridProps) => {
  const gridStyles = {
    '--grid-angle': `${angle}deg`,
    '--cell-size': `${cellSize}px`,
    '--grid-opacity': opacity,
    '--grid-line': lineColor,
  } as React.CSSProperties;

  return (
    <div
      className="pointer-events-none absolute inset-0 overflow-hidden [perspective:220px]"
      style={gridStyles}
    >
      <div className="absolute inset-0 [transform:rotateX(var(--grid-angle))]">
        <div className="h-[280vh] w-[600vw] origin-top-left animate-grid bg-[linear-gradient(to_right,var(--grid-line)_1px,transparent_0),linear-gradient(to_bottom,var(--grid-line)_1px,transparent_0)] bg-[size:var(--cell-size)_var(--cell-size)] opacity-[var(--grid-opacity)]" />
      </div>
      <div className="absolute inset-0 bg-gradient-to-t from-background via-background/70 to-transparent" />
    </div>
  );
};

export const HeroSectionDark = React.forwardRef<HTMLDivElement, HeroSectionProps>(
  (
    {
      className,
      title = 'AI Contract Intelligence',
      subtitle = {
        regular: 'Understand every clause with ',
        gradient: 'production-ready legal AI workflows.',
      },
      description = 'LexAI turns contract review into a structured, explainable workflow with clause extraction, risk scoring, and plain-English negotiation guidance.',
      ctaText = 'Start Analysis',
      ctaHref = '/analyze',
      secondaryText = 'View Repository',
      secondaryHref = 'https://github.com/Vishnu-VJ24/Legal-Risk-Sentinel',
      gridOptions,
      ...props
    },
    ref,
  ) => {
    return (
      <div
        ref={ref}
        {...props}
        className={cn('relative overflow-hidden', className)}
      >
        <section className="relative z-10 mx-auto max-w-screen-xl">
          <RetroGrid {...gridOptions} />
          <div className="px-6 py-20 sm:px-10 lg:px-12 lg:py-28">
            <div className="mx-auto max-w-4xl text-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-border bg-background/40 px-5 py-2 text-sm font-medium text-text-secondary backdrop-blur">
                <span>{title}</span>
                <ChevronRight className="h-4 w-4 text-primary transition-transform duration-300 group-hover:translate-x-1" />
              </div>
              <h1 className="mt-6 text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
                <span>{subtitle.regular}</span>
                <span className="bg-gradient-to-r from-primary via-secondary to-primary bg-clip-text text-transparent">
                  {subtitle.gradient}
                </span>
              </h1>
              <p className="mx-auto mt-6 max-w-2xl text-base leading-8 text-text-secondary sm:text-lg">
                {description}
              </p>
              <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
                <ButtonWithIcon href={ctaHref} label={ctaText} />
                <a
                  href={secondaryHref}
                  className="inline-flex items-center justify-center rounded-full border border-border bg-background/60 px-8 py-4 text-sm font-semibold text-text-primary transition hover:border-primary/40"
                >
                  {secondaryText}
                </a>
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  },
);

HeroSectionDark.displayName = 'HeroSectionDark';

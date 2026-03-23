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
      ...props
    },
    ref,
  ) => {
    return (
      <div
        ref={ref}
        {...props}
        className={cn('relative', className)}
      >
        <section className="relative z-10 mx-auto max-w-screen-xl px-6 py-20 sm:px-10 lg:px-12 lg:py-28">
          <div className="mx-auto max-w-4xl text-center">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-black/25 px-5 py-2 text-sm font-medium text-text-secondary backdrop-blur-md">
              <span>{title}</span>
              <ChevronRight className="h-4 w-4 text-primary" />
            </div>
            <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-text-primary sm:text-5xl lg:text-7xl">
              <span>{subtitle.regular}</span>
              <span className="bg-gradient-to-r from-fuchsia-400 via-violet-400 to-purple-300 bg-clip-text text-transparent">
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
                className="inline-flex items-center justify-center rounded-full border border-white/10 bg-black/25 px-8 py-4 text-sm font-semibold text-text-primary transition hover:border-primary/40 hover:bg-black/35"
              >
                {secondaryText}
              </a>
            </div>
          </div>
        </section>
      </div>
    );
  },
);

HeroSectionDark.displayName = 'HeroSectionDark';

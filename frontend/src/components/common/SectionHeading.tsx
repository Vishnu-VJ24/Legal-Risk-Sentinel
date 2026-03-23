import type { ReactNode } from 'react';

interface SectionHeadingProps {
  eyebrow: string;
  title: string;
  description: ReactNode;
}

export const SectionHeading = ({ eyebrow, title, description }: SectionHeadingProps) => {
  return (
    <div className="max-w-3xl">
      <p className="text-sm uppercase tracking-[0.24em] text-secondary">{eyebrow}</p>
      <h1 className="mt-3 text-4xl font-extrabold tracking-tight sm:text-5xl">{title}</h1>
      <p className="mt-4 text-base leading-8 text-text-secondary sm:text-lg">{description}</p>
    </div>
  );
};

import type { AnchorHTMLAttributes } from 'react';
import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '../../utils/cn';

interface ButtonWithIconProps extends AnchorHTMLAttributes<HTMLAnchorElement> {
  label: string;
}

export const ButtonWithIcon = ({ className, href, label, ...props }: ButtonWithIconProps) => {
  const sharedClassName = cn(
    'group relative inline-flex h-12 items-center overflow-hidden rounded-full border border-primary/30 bg-primary px-6 pe-14 text-sm font-semibold text-white transition-all duration-500 hover:pe-6 hover:ps-14 hover:shadow-glow',
    className,
  );

  const content = (
    <>
      <span className="relative z-10 transition-all duration-500">{label}</span>
      <span className="absolute right-1 flex h-10 w-10 items-center justify-center rounded-full bg-background text-text-primary transition-all duration-500 group-hover:right-[calc(100%-44px)] group-hover:rotate-45">
        <ArrowUpRight className="h-4 w-4" />
      </span>
    </>
  );

  if (href?.startsWith('/')) {
    return (
      <Link to={href} className={sharedClassName}>
        {content}
      </Link>
    );
  }

  return (
    <a
      href={href}
      className={sharedClassName}
      {...props}
    >
      {content}
    </a>
  );
};

import { Scale } from 'lucide-react';
import { Link, NavLink } from 'react-router-dom';
import { ThemeToggle } from '../theme/ThemeToggle';
import { cn } from '../../utils/cn';

const navItems = [
  { to: '/', label: 'Home' },
  { to: '/analyze', label: 'Analyze' },
];

export const Header = () => {
  return (
    <header className="sticky top-0 z-40 border-b border-border/80 bg-background/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-3 text-lg font-semibold text-text-primary">
          <span className="rounded-2xl border border-primary/40 bg-primary/10 p-2 text-primary">
            <Scale className="h-5 w-5" />
          </span>
          <span>LexAI</span>
        </Link>
        <div className="flex items-center gap-4">
          <nav className="hidden items-center gap-1 sm:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'rounded-full px-4 py-2 text-sm text-text-secondary transition hover:text-text-primary',
                    isActive && 'bg-surface text-text-primary',
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
};

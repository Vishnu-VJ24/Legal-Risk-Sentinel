import { MoonStar, SunMedium } from 'lucide-react';
import { useTheme } from './useTheme';

export const ThemeToggle = () => {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      aria-label="Toggle theme"
      onClick={toggleTheme}
      className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-2 text-sm text-text-secondary transition hover:border-primary/50 hover:text-text-primary"
    >
      {theme === 'dark' ? <SunMedium className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
      {theme === 'dark' ? 'Light' : 'Dark'}
    </button>
  );
};

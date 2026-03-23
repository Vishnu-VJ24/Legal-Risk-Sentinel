import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: 'rgb(var(--color-background) / <alpha-value>)',
        surface: 'rgb(var(--color-surface) / <alpha-value>)',
        border: 'rgb(var(--color-border) / <alpha-value>)',
        primary: 'rgb(var(--color-primary) / <alpha-value>)',
        secondary: 'rgb(var(--color-secondary) / <alpha-value>)',
        text: {
          primary: 'rgb(var(--color-text-primary) / <alpha-value>)',
          secondary: 'rgb(var(--color-text-secondary) / <alpha-value>)',
        },
        risk: {
          low: 'rgb(var(--color-risk-low) / <alpha-value>)',
          medium: 'rgb(var(--color-risk-medium) / <alpha-value>)',
          high: 'rgb(var(--color-risk-high) / <alpha-value>)',
          critical: 'rgb(var(--color-risk-critical) / <alpha-value>)',
        },
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(108, 99, 255, 0.3), 0 0 40px rgba(108, 99, 255, 0.22)',
      },
      backgroundImage: {
        'hero-gradient':
          'radial-gradient(circle at top, rgba(108,99,255,0.2), transparent 30%), radial-gradient(circle at bottom right, rgba(0,212,170,0.15), transparent 25%)',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      keyframes: {
        pulseRing: {
          '0%': { boxShadow: '0 0 0 0 rgba(108,99,255,0.4)' },
          '100%': { boxShadow: '0 0 0 16px rgba(108,99,255,0)' },
        },
      },
      animation: {
        pulseRing: 'pulseRing 1.2s ease-out',
      },
    },
  },
  plugins: [],
} satisfies Config;

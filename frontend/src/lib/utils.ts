import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const normalizeSeverityLabel = (severity?: string | null) => {
  const value = severity?.toUpperCase().trim();
  if (value === 'CRITICAL' || value === 'HIGH' || value === 'MEDIUM' || value === 'LOW') {
    return value;
  }
  return 'LOW';
};

export const getSeverityBadgeStyles = (severity: string) => {
  switch (normalizeSeverityLabel(severity)) {
    case 'CRITICAL': return 'bg-red-600 text-white border-red-700 hover:bg-red-700';
    case 'HIGH': return 'bg-orange-500 text-white border-orange-600 hover:bg-orange-600';
    case 'MEDIUM': return 'bg-amber-400 text-amber-950 border-amber-500 hover:bg-amber-500';
    case 'LOW': return 'bg-slate-500 text-white border-slate-600 hover:bg-slate-600';
    default: return 'bg-muted text-muted-foreground border-border';
  }
};

export const getSeverityCardStyles = (severity: string) => {
  switch (normalizeSeverityLabel(severity)) {
    case 'CRITICAL': return 'bg-red-500/10 border-red-200 text-red-900';
    case 'HIGH': return 'bg-orange-500/10 border-orange-200 text-orange-900';
    case 'MEDIUM': return 'bg-amber-500/10 border-amber-200 text-amber-900';
    case 'LOW': return 'bg-slate-500/10 border-slate-200 text-slate-900';
    default: return 'bg-muted border-border';
  }
};

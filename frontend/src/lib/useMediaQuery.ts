import { useSyncExternalStore } from 'react';

export function useMediaQuery(query: string): boolean {
  const subscribe = (listener: () => void) => {
    const media = window.matchMedia(query);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  };
  const getSnapshot = () => window.matchMedia(query).matches;
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}

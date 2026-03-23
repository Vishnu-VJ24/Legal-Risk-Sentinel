import { useEffect, useState } from 'react';

interface AnimatedNumberProps {
  value: number;
}

export const AnimatedNumber = ({ value }: AnimatedNumberProps) => {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const start = performance.now();
    const duration = 1100;
    let frameId = 0;

    const tick = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      setDisplayValue(Math.round(value * progress));
      if (progress < 1) {
        frameId = window.requestAnimationFrame(tick);
      }
    };

    frameId = window.requestAnimationFrame(tick);
    return () => window.cancelAnimationFrame(frameId);
  }, [value]);

  return <span>{displayValue}</span>;
};

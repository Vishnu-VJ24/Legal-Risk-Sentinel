import { motion } from 'framer-motion';
import type { HTMLAttributes, PropsWithChildren } from 'react';
import { useEffect, useRef } from 'react';
import { cn } from '../../utils/cn';

interface VortexProps extends PropsWithChildren {
  className?: string;
  containerClassName?: string;
  particleCount?: number;
  backgroundColor?: string;
  baseHue?: number;
}

export const Vortex = ({
  children,
  className,
  containerClassName,
  particleCount = 220,
  backgroundColor = 'transparent',
  baseHue = 300,
}: VortexProps & HTMLAttributes<HTMLDivElement>) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }

    let frameId = 0;
    let tick = 0;
    const particles = Array.from({ length: particleCount }, () => ({
      x: Math.random(),
      y: Math.random(),
      driftX: (Math.random() - 0.5) * 0.001,
      driftY: (Math.random() - 0.5) * 0.00075,
      size: 0.8 + Math.random() * 5.4,
      pulse: Math.random() * Math.PI * 2,
      swirl: Math.random() * Math.PI * 2,
    }));

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    const draw = () => {
      tick += 1;
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, width, height);

      particles.forEach((particle, index) => {
        particle.x = (particle.x + particle.driftX + 1) % 1;
        particle.y = (particle.y + particle.driftY + 1) % 1;

        const swirlRadius = 12 + (index % 7) * 4;
        const x = particle.x * width + Math.cos(tick * 0.006 + particle.swirl) * swirlRadius;
        const y = particle.y * height + Math.sin(tick * 0.007 + particle.swirl) * swirlRadius;
        const hue =
          index % 6 === 0
            ? 148 + ((tick * 0.18 + index * 3) % 24)
            : baseHue + ((index * 11 + tick * 0.28) % 34);
        const alpha = 0.26 + ((index % 5) * 0.07);
        const radius = particle.size + Math.sin(tick * 0.012 + particle.pulse) * 0.8;

        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${hue}, 100%, 72%, ${alpha})`;
        ctx.shadowColor = `hsla(${hue}, 100%, 68%, 0.9)`;
        ctx.shadowBlur = 44;
        ctx.fill();
      });

      frameId = window.requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener('resize', resize);

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener('resize', resize);
    };
  }, [backgroundColor, baseHue, particleCount]);

  return (
    <div className={cn('relative h-full w-full overflow-hidden', containerClassName)}>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute inset-0 z-0 opacity-90 mix-blend-screen"
      >
        <canvas ref={canvasRef} className="h-full w-full" />
      </motion.div>
      <div className={cn('relative z-10', className)}>{children}</div>
    </div>
  );
};

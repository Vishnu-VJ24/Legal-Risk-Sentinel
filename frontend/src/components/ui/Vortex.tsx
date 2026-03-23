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
  particleCount = 90,
  backgroundColor = 'transparent',
  baseHue = 250,
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
    const particles = Array.from({ length: particleCount }, (_, index) => ({
      angle: (index / particleCount) * Math.PI * 2,
      radius: 40 + Math.random() * 220,
      speed: 0.002 + Math.random() * 0.006,
      size: 0.8 + Math.random() * 2.4,
      offset: Math.random() * Math.PI * 2,
    }));

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    const draw = () => {
      tick += 1;
      const width = canvas.width;
      const height = canvas.height;
      const centerX = width / 2;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, width, height);

      particles.forEach((particle, index) => {
        const wobble = Math.sin(tick * 0.012 + particle.offset) * 24;
        const radius = particle.radius + wobble;
        const angle = particle.angle + tick * particle.speed;
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle * 1.6) * radius * 0.35;
        const hue = baseHue + ((index * 7 + tick * 0.4) % 70);

        ctx.beginPath();
        ctx.arc(x, y, particle.size, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${hue}, 100%, 68%, 0.7)`;
        ctx.shadowColor = `hsla(${hue}, 100%, 68%, 0.55)`;
        ctx.shadowBlur = 16;
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
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="absolute inset-0 z-0">
        <canvas ref={canvasRef} className="h-full w-full" />
      </motion.div>
      <div className={cn('relative z-10', className)}>{children}</div>
    </div>
  );
};

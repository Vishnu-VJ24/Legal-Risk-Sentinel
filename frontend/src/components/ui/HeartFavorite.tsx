import { motion } from 'framer-motion';
import { Heart } from 'lucide-react';
import { useState } from 'react';
import { cn } from '../../utils/cn';

interface HeartFavoriteProps {
  href?: string;
  label?: string;
  className?: string;
}

export const HeartFavorite = ({
  href = 'https://github.com/Vishnu-VJ24',
  label = 'Follow Vishnu on GitHub',
  className,
}: HeartFavoriteProps) => {
  const [isLiked, setIsLiked] = useState(false);

  return (
    <motion.a
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label={label}
      title={label}
      onClick={() => setIsLiked((current) => !current)}
      whileTap={{ scale: 0.94 }}
      className={cn(
        'group inline-flex items-center gap-3 rounded-full border border-white/10 bg-black/30 px-3 py-3 text-sm text-text-secondary shadow-[0_20px_60px_rgba(0,0,0,0.35)] backdrop-blur-md transition hover:border-fuchsia-400/40 hover:text-text-primary',
        className,
      )}
    >
      <motion.span
        animate={{
          scale: isLiked ? [1, 1.28, 1] : 1,
        }}
        transition={{
          duration: 0.32,
          ease: 'easeInOut',
        }}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-white/5"
      >
        <Heart
          className={cn(
            'h-5 w-5 transition-colors',
            isLiked ? 'fill-pink-500 text-pink-500' : 'text-fuchsia-300 group-hover:text-pink-400',
          )}
        />
      </motion.span>
      <span className="hidden whitespace-nowrap pr-2 font-medium sm:inline">{label}</span>
    </motion.a>
  );
};

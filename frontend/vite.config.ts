import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const repoName = 'Legal-Risk-Sentinel';

export default defineConfig(({ command }) => ({
  base: command === 'build' ? `/${repoName}/` : '/',
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          pdf: ['react-pdf', 'pdfjs-dist'],
          charts: ['recharts'],
          motion: ['framer-motion'],
        },
      },
    },
  },
  server: {
    port: 5173,
  },
}));

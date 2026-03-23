import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const repoName = 'Legal-Risk-Sentinel';

export default defineConfig(({ command }) => ({
  base: command === 'build' ? `/${repoName}/` : '/',
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-recharts': ['recharts'],
          pdf: ['react-pdf', 'pdfjs-dist'],
          motion: ['framer-motion'],
        },
      },
    },
  },
  server: {
    port: 5173,
  },
}));

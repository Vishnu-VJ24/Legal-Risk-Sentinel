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
        entryFileNames: 'assets/[name].js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name?.endsWith('.css')) {
            return 'assets/[name].css';
          }
          return 'assets/[name][extname]';
        },
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

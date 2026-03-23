import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
var repoName = 'lexai';
export default defineConfig({
    base: process.env.NODE_ENV === 'production' ? "/".concat(repoName, "/") : '/',
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
});

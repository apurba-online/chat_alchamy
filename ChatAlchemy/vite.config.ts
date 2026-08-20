import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [react()],
  optimizeDeps: { exclude: ['lucide-react'] },
  server: {
    fs: { strict: false, allow: ['..'] },
    // Production uses same-origin Vercel `/api/*` functions. During local
    // development the FastAPI backend runs on port 8000, so keep the frontend
    // API client same-origin and proxy only the API namespace here.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  publicDir: 'public',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    rollupOptions: { input: { main: resolve(__dirname, 'index.html') }, },
  },
});

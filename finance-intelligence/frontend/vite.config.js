import { defineConfig } from 'vite';
export default defineConfig({
  server: { port: 5173, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { rollupOptions: { output: { manualChunks: {
    react: ['react', 'react-dom'], charts: ['recharts'], markdown: ['react-markdown'],
  } } } },
});

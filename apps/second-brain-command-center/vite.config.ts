import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// READ-ONLY Command Center. Dev server proxies /api to the thin BFF so the
// browser never holds credentials and there is no CORS surface in production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8790',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})

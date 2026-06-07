import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy: routes /api/* to FastAPI on port 8000 (local dev only).
// In production, Nginx handles this proxy.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
        changeOrigin: true,
        ws: true,
      },
    },
  },
})

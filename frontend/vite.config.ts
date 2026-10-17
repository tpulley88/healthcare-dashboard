import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development, forward /api to FastAPI the same way nginx does in Docker.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.API_URL ?? 'http://localhost:8000',
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})

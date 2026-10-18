import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

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
  test: {
    // Run date and time tests in a fixed timezone, whatever the machine's own setting.
    env: { TZ: 'America/New_York' },
  },
})

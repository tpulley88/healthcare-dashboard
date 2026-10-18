import { defineConfig, devices } from '@playwright/test'

/**
 * Browser tests against the running Docker Compose stack (`docker compose up`).
 *
 * They use the same database as the app, so each test creates its own patients
 * and deletes them afterwards, and never edits the seeded ones.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:8080',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})

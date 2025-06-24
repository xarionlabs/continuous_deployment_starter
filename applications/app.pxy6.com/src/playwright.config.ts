import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './app/routes/__tests__',
  testMatch: '**/*.test.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1, // Run tests serially to avoid port conflicts
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on',
  },
  projects: [
    {
      name: 'api',
      testMatch: '**/api.webhooks.compliance.*.test.ts',
    },
  ],
  // Disable web server since we're testing API routes directly
  webServer: undefined,
});

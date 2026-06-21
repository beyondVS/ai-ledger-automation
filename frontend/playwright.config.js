import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright Global Configuration for PWA E2E Testing
 * - Target directory: ./tests/e2e
 * - Integrates auto-start web server for frontend vite on port 5173
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    permissions: ["notifications"],
    launchOptions: {
      args: [
        "--unsafely-treat-insecure-origin-as-secure=http://localhost:5173",
      ]
    }
  },
  projects: [
    {
      name: "chromium",
      use: { 
        ...devices["Desktop Chrome"],
        permissions: ["notifications"],
        launchOptions: {
          args: [
            "--unsafely-treat-insecure-origin-as-secure=http://localhost:5173",
          ]
        }
      },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:5173",
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});

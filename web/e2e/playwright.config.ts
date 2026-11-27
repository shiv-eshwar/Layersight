import { defineConfig, devices } from "@playwright/test";

const target = process.env.E2E_TARGET ?? "harness";
const port = process.env.HARNESS_PORT ?? "4173";
const baseURL =
  process.env.E2E_BASE_URL ??
  (target === "app" ? "http://127.0.0.1:3000" : `http://127.0.0.1:${port}`);

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.ts",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "on-first-retry",
    video: process.env.DEMO_VIDEO ? "on" : "off",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer:
    target === "harness"
      ? {
          command: "node harness/server.mjs",
          url: `${baseURL}/health`,
          reuseExistingServer: !process.env.CI,
          timeout: 30_000,
          env: { HARNESS_PORT: port },
        }
      : undefined,
});

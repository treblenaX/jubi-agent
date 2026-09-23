import { defineConfig, devices } from "@playwright/test";
import path from "path";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["html"], ["github"]],

  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    storageState: "playwright/.auth/user.json",
  },

  globalSetup: "./global-setup.ts",

  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "uvicorn app.main:app --port 2024 --env-file .env.test",
      url: "http://localhost:2024/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      cwd: path.resolve(__dirname, "../server"),
    },
  ],

  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
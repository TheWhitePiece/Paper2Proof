import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 240000,
  expect: { timeout: 30000 },
  workers: 1,
  use: { baseURL: "http://127.0.0.1:3000", browserName: "chromium", channel: "chrome", headless: true, viewport: { width: 1280, height: 900 }, trace: "retain-on-failure" },
});

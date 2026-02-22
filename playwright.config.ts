import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: 'http://127.0.0.1:3000',
    headless: true,
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'mkdir -p tmp && DATABASE_URL=sqlite:///./tmp/votodb_playwright.db ./.venv/bin/python init_database.py && set -a && . backend/.env && set +a && DATABASE_URL=sqlite:///./tmp/votodb_playwright.db PYTHONPATH=backend ./.venv/bin/python -m uvicorn backend.main_v2:app --host 127.0.0.1 --port 8001',
      url: 'http://127.0.0.1:8001/health',
      timeout: 120_000,
      reuseExistingServer: true,
    },
    {
      command: 'npm --prefix frontend start',
      url: 'http://127.0.0.1:3000',
      timeout: 180_000,
      reuseExistingServer: true,
    },
  ],
});

import { defineConfig } from '@playwright/test';

const E2E_BACKEND_URL = 'http://127.0.0.1:18001';
const E2E_FRONTEND_URL = 'http://127.0.0.1:3100';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: E2E_FRONTEND_URL,
    headless: true,
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: `mkdir -p tmp && DATABASE_URL=sqlite:///./tmp/votodb_playwright.db ./.venv/bin/python init_database.py && set -a && . backend/.env && set +a && DATABASE_URL=sqlite:///./tmp/votodb_playwright.db PYTHONPATH=backend ./.venv/bin/python -m uvicorn backend.main_v2:app --host 127.0.0.1 --port 18001`,
      url: `${E2E_BACKEND_URL}/health`,
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: `PORT=3100 REACT_APP_API_URL=${E2E_BACKEND_URL} npm --prefix frontend start`,
      url: E2E_FRONTEND_URL,
      timeout: 180_000,
      reuseExistingServer: false,
    },
  ],
});

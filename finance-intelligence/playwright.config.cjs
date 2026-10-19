const { defineConfig } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const localPython = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const python = process.env.PYTHON || (fs.existsSync(localPython) ? localPython : 'python');
module.exports = defineConfig({
  testDir: './frontend/tests', timeout: 45000, workers: 1,
  use: { baseURL: 'http://127.0.0.1:8765', headless: true, viewport: { width: 1440, height: 1050 },
    channel: process.env.PLAYWRIGHT_CHANNEL || (process.platform === 'win32' ? 'msedge' : 'chromium'),
    screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  webServer: { command: `"${python}" -m uvicorn backend.main:app --host 127.0.0.1 --port 8765`,
    url: 'http://127.0.0.1:8765/api/health', timeout: 30000, reuseExistingServer: false,
    env: { AI_DISABLED: '1' } },
});

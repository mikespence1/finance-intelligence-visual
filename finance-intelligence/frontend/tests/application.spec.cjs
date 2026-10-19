const { test, expect } = require('@playwright/test');
const path = require('node:path');

test('report filters, navigation, export and uploads work together', async ({ page }) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Financial Performance', exact: true })).toBeVisible();
  await expect(page.getByText('Preparing Your Reporting Workspace…')).toBeHidden();
  await expect(page.getByRole('img', { name: 'Revenue actual versus budget and forecast trend' })).toBeVisible();
  await page.screenshot({ path: 'test-results/performance-desktop.png', fullPage: true });
  await page.getByLabel('Reporting View', { exact: true }).selectOption('Quarter');
  await expect(page.getByLabel('Reporting Period')).toHaveValue('2026Q4');
  await page.getByLabel('Compare Actuals Against').selectOption('forecast');
  await expect(page.getByRole('img', { name: 'Revenue actual versus forecast trend', exact: true })).toBeVisible();
  await page.getByRole('navigation').getByRole('button', { name: 'Sustainability & Operations' }).click();
  await expect(page.getByRole('heading', { name: 'Sustainable Materials & Manufacturing' })).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Materials & Circularity' })).toBeVisible();
  await page.getByRole('navigation').getByRole('button', { name: 'Board Pack', exact: true }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download PPTX' }).click();
  expect((await download).suggestedFilename()).toBe('sustainable_packaging_board_2026Q4.pptx');
  await page.getByRole('button', { name: 'Manage Data' }).click();
  for (const [label, name] of [['Financial Accounts', 'finance'], ['Operations & Materials', 'operations'], ['Closing Balances & Headcount', 'balances']]) {
    await page.getByLabel(label, { exact: true }).setInputFiles(path.resolve(`data/${name}.csv`));
  }
  await page.getByRole('button', { name: 'Validate & Load Files' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await expect(page.locator('.source-pill')).toHaveText('Uploaded Data');
  await page.getByRole('button', { name: 'Manage Data' }).click();
  await page.getByRole('button', { name: 'Load Seasonal Sample Data' }).click();
  await expect(page.locator('.source-pill')).toHaveText('Synthetic Sample Data');
  expect(errors).toEqual([]);
});

test('AI report and grounded chat render responses and sources', async ({ page }) => {
  await page.route('**/api/commentary', route => route.fulfill({ json: { text: '## Executive Summary\nTest briefing.', sections: [{ title: 'Executive Summary', body: 'Synthetic results for this reporting period.' }] } }));
  await page.route('**/api/chat', route => route.request().method() === 'POST' ? route.fulfill({ json: {
    status: 'answered', answer: 'Synthetic revenue is shown below.', limitation: '', source_ids: ['S1'],
    evidence: [{ 'Source ID': 'S1', Metric: 'Revenue', Value: 100, Period: 'December 2026' }],
  } }) : route.continue());
  await page.goto('/');
  await expect(page.getByText('Preparing Your Reporting Workspace…')).toBeHidden();
  await page.getByRole('navigation').getByRole('button', { name: 'AI Report', exact: true }).click();
  await page.getByRole('button', { name: 'Generate Briefing' }).click();
  await expect(page.getByRole('heading', { name: 'Executive Summary' })).toBeVisible();
  await page.getByRole('navigation').getByRole('button', { name: 'Ask Your Data', exact: true }).click();
  const metricsBox = await page.locator('.headline-grid').boundingBox();
  const promptBox = await page.locator('.chat-input').boundingBox();
  const examplesBox = await page.getByRole('heading', { name: 'Example Questions' }).boundingBox();
  expect(promptBox.y).toBeGreaterThanOrEqual(metricsBox.y + metricsBox.height);
  expect(promptBox.y).toBeLessThan(examplesBox.y);
  await page.getByLabel('Your Question').fill('What was revenue?');
  await page.getByRole('button', { name: 'Send question' }).click();
  await expect(page.getByText('Synthetic revenue is shown below.')).toBeVisible();
  const answerBox = await page.locator('.chat-message.assistant').boundingBox();
  const answeredPromptBox = await page.locator('.chat-input').boundingBox();
  expect(answerBox.y).toBeLessThan(answeredPromptBox.y);
  await page.screenshot({ path: 'test-results/ask-your-data-desktop.png', fullPage: true });
  await page.getByText('Supporting Data & Calculations', { exact: true }).click();
  await expect(page.locator('.evidence')).toContainText('Revenue');
  await page.getByRole('button', { name: 'Clear Chat' }).click();
  await expect(page.getByText('Synthetic revenue is shown below.')).toBeHidden();
});

test('mobile layout keeps navigation, cards and charts inside the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.getByText('Preparing Your Reporting Workspace…')).toBeHidden();
  await expect(page.getByRole('heading', { name: 'Financial Performance', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/performance-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Open navigation' }).click();
  await page.getByRole('navigation').getByRole('button', { name: 'Board Pack', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Board Pack', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});


test('templates download and partial upload show No Data cards', async ({ page }) => {
  await page.goto('/');
  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: 'Templates', exact: true }).click();
  expect((await download).suggestedFilename()).toBe('data_load_templates.zip');
  await page.getByRole('button', { name: 'Manage Data' }).click();
  await page.getByLabel('Financial Accounts', { exact: true }).setInputFiles({
    name: 'partial.csv', mimeType: 'text/csv',
    buffer: Buffer.from('period,scenario,account,amount\n2026-01-01,actual,Revenue,100\n'),
  });
  await page.getByRole('button', { name: 'Validate & Load Files' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  const ebitda = page.locator('.headline-grid .metric-card').filter({ has: page.locator('.metric-title', { hasText: /^EBITDA$/ }) });
  await expect(ebitda.locator('.metric-value')).toHaveText('No Data');
  await expect(page.locator('.focus-metric').filter({ hasText: 'Cash' }).locator('strong')).toHaveText('No Data');
});

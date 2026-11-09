const { test, expect } = require('@playwright/test');
test('executive reporting filters and accessible sections', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Executive Dashboard' }).click();
  await expect(page.getByRole('heading', { name: 'Your reporting view' })).toBeVisible();
  await expect(page.getByLabel('Location', { exact: true }).getByRole('option')).toHaveText(['All locations','Abu Dhabi','Dubai','KSA','Other Emirates']);
  await page.getByRole('button', { name: 'Customer performance', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Bottom 10 customers by gross profit' })).toBeVisible();
  await page.getByLabel('Analysis period', { exact: true }).selectOption('ytd');
  await expect(page.getByText('Analysis: 2026-01-01 to 2026-11-09.', { exact: false })).toBeVisible();
  await page.getByLabel('Rank customers by').selectOption('net_revenue');
  await page.getByLabel('Customers in each list').selectOption('5');
  await expect(page.getByRole('heading', { name: 'Bottom 5 customers by revenue' })).toBeVisible();
  await page.getByLabel('Location', { exact: true }).selectOption('KSA');
  await page.getByRole('button', { name: 'Trends & comparisons', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Revenue trend - selected period' })).toBeVisible();
  await expect(page.getByText('EBITDA', { exact: true })).toHaveCount(0);
  expect(await page.locator('.executive-dashboard').innerText()).not.toContain('\uFFFD');
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('button', {name:'Sales overview', exact:true})).toBeVisible();
  await page.screenshot({ path: 'test-results/executive-mobile.png', fullPage: true });
});

test('executive load failure can be retried', async ({ page }) => {
  let failed = true;
  await page.route('**/api/executive?*', async route => {
    if (failed) await route.fulfill({status: 500, contentType: 'text/plain', body: 'Internal Server Error'});
    else await route.continue();
  });
  await page.goto('/');
  await page.getByRole('button', {name: 'Executive Dashboard', exact: true}).click();
  await expect(page.getByRole('alert')).toContainText('HTTP 500');
  failed = false;
  await page.getByRole('button', {name: 'Retry Executive Dashboard'}).click();
  await expect(page.getByRole('heading', {name: 'Your reporting view'})).toBeVisible();
});

test('executive incompatible API response shows an actionable error', async ({ page }) => {
  await page.route('**/api/executive?*', route => route.fulfill({status: 200, contentType: 'application/json', body: JSON.stringify({customers: []})}));
  await page.goto('/');
  await page.getByRole('button', {name: 'Executive Dashboard', exact: true}).click();
  await expect(page.getByRole('alert')).toContainText('Redeploy the frontend and backend');
  await expect(page.getByRole('button', {name: 'Retry Executive Dashboard'})).toBeVisible();
});

test('Executive chat sends dashboard filters and displays supporting calculations', async ({ page }) => {
  let received;
  await page.route('**/api/executive/chat', async route => {
    if (route.request().method() !== 'POST') return route.continue();
    received = route.request().postDataJSON();
    await route.fulfill({contentType:'application/json',body:JSON.stringify({answer:'Synthetic sample gross profit is AED 100 [S1].',limitation:'',source_ids:['S1'],evidence:[{'Source ID':'S1',Dataset:'Executive ERP',gross_profit:100}]})});
  });
  await page.goto('/');
  await page.getByRole('button',{name:'Executive Dashboard',exact:true}).click();
  await page.getByLabel('Location',{exact:true}).selectOption('KSA');
  const chat=page.getByRole('region',{name:'Ask Executive Data'});
  await expect(chat.getByRole('button',{name:'Ask',exact:true})).toBeDisabled();
  await chat.getByLabel('Question about Executive data').fill('Who are the top customers?');
  await expect(chat.getByRole('button',{name:'Ask',exact:true})).toBeEnabled();
  await chat.getByRole('button',{name:'Ask',exact:true}).click();
  await expect(chat.getByText('Synthetic sample gross profit is AED 100 [S1].')).toBeVisible();
  expect(received.location).toBe('KSA');
  expect(received.period).toBe('mtd');
  await chat.getByText('Supporting Executive ERP calculations').click();
  await expect(chat.getByRole('cell',{name:'Executive ERP',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Ask Your Data',exact:true})).toHaveCount(0);
});

test('rounded ranking bars and matched-period trends remain accessible', async ({page}) => {
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await page.getByRole('button',{name:'Executive Dashboard',exact:true}).click();
  await page.getByRole('button',{name:'Customer performance',exact:true}).click();
  const top=page.locator('.executive-ranking-visual').filter({has:page.getByRole('heading',{name:'Top 10 customers by gross profit',exact:true})});
  await expect(top.locator('.recharts-bar-rectangle').first()).toBeVisible();
  await expect(top.getByText('Same time last month',{exact:true})).toBeVisible();
  await expect(top.getByText('Same time last year',{exact:true})).toBeVisible();
  const focus=top.getByLabel('Trend focus for Top 10 customers by gross profit');
  const name=await focus.locator('option').nth(1).textContent();
  await focus.selectOption(name);
  await expect(top.getByRole('heading',{name:`${name} - period progress`,exact:true})).toBeVisible();
  await top.getByText('View exact figures',{exact:true}).click();
  await expect(top.getByRole('columnheader',{name:'Gross margin',exact:true})).toBeVisible();
  await page.screenshot({path:'test-results/executive-charts-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await expect(focus).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/executive-charts-mobile.png',fullPage:true});
  expect(errors).toEqual([]);
});

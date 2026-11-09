const {test,expect}=require('@playwright/test');

test('persistent page-scoped assistants, metric explanations and operational themes',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  const financial=page.getByRole('complementary',{name:'Financial Data side panel'});
  await expect(financial.getByRole('heading',{name:'Ask your Financial Data'})).toBeVisible();
  await expect(financial).toHaveCSS('background-color','rgb(11, 31, 51)');
  await expect(page.getByText('Built For',{exact:true})).toHaveCount(0);
  const info=page.locator('.metric-explainer').filter({hasText:/^EBITDA$/}).first();
  await expect(info).toHaveAttribute('title',/Earnings Before Interest/);
  await info.focus();
  const panelBox=await financial.boundingBox();const metricsBox=await page.locator('.dashboard-metrics').boundingBox();
  expect(panelBox.x).toBeGreaterThan(metricsBox.x);
  await page.screenshot({path:'test-results/financial-sidebar-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Sustainability & Operations',exact:true}).click();
  await expect(page.getByRole('region',{name:'Operational headline metrics'}).locator('.metric-card')).toHaveCount(4);
  await expect(page.locator('.operations-overview > .headline-grid')).not.toContainText('EBITDA');
  await expect(page.getByRole('heading',{name:'Materials & Circularity',exact:true})).toBeVisible();
  await page.getByRole('navigation',{name:'Operational themes'}).getByRole('button',{name:'Customer Returns'}).click();
  await expect(page.getByRole('heading',{name:'Customer Returns',exact:true})).toBeVisible();
  await expect(page.getByLabel('Operational trend metric')).toHaveValue('Return Rate %');
  await page.getByRole('navigation',{name:'Operational themes'}).getByRole('button',{name:'Cash, Suppliers & People'}).click();
  await page.getByText('All 9 cash, suppliers & people measures and plan comparisons').click();
  await expect(page.locator('.metric-explainer').filter({hasText:/^DSO$/})).toHaveAttribute('title',/Days Sales Outstanding/);
  await page.screenshot({path:'test-results/operations-themes.png',fullPage:true});
  await page.getByRole('button',{name:'Executive Dashboard',exact:true}).click();
  const executive=page.getByRole('complementary',{name:'Executive Data side panel'});
  await expect(executive.getByRole('heading',{name:'Ask your Executive Data'})).toBeVisible();
  await expect(executive).toHaveCSS('background-color','rgb(11, 31, 51)');
  await expect(page.getByText('Data coverage and metric definitions',{exact:true})).toHaveCount(0);
  const plan=page.getByRole('img',{name:'Selected-period revenue compared with budget and forecast'});
  await expect(plan.locator('.recharts-bar-rectangle').first()).toBeVisible();
  const box=await plan.locator('.recharts-bar-rectangle').first().boundingBox();expect(box.height).toBeGreaterThan(box.width);
  await page.getByRole('button',{name:'Customer performance',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Top 10 customers by gross profit',exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Bottom 10 customers by gross profit',exact:true})).toBeVisible();
  const bottom=page.locator('.executive-ranking-visual').filter({has:page.getByRole('heading',{name:'Bottom 10 customers by gross profit',exact:true})});
  await expect(bottom.locator('.recharts-bar-rectangle path').first()).toHaveAttribute('fill','#0B1F33');
  await page.getByRole('button',{name:'Product performance',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Top 10 SKUs by revenue',exact:true})).toBeVisible();
  await page.screenshot({path:'test-results/executive-sidebar-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await expect(executive).toHaveCSS('position','sticky');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/executive-sidebar-mobile.png',fullPage:true});
  expect(errors).toEqual([]);
});

test('financial side panel posts only to the scoped financial endpoint',async({page})=>{
  let body;
  await page.route('**/api/financial/chat',route=>{
    if(route.request().method()!=='POST')return route.continue();
    body=route.request().postDataJSON();
    return route.fulfill({json:{answer:'Synthetic financial EBITDA [S1].',source_ids:['S1'],evidence:[{'Source ID':'S1',Metric:'EBITDA',Value:100}],limitation:''}});
  });
  await page.goto('/');
  const panel=page.getByRole('complementary',{name:'Financial Data side panel'});
  await panel.getByLabel('Question about Financial Data').fill('What is EBITDA?');
  await panel.getByRole('button',{name:'Ask',exact:true}).click();
  await expect(panel.getByText('Synthetic financial EBITDA [S1].')).toBeVisible();
  expect(body.question).toBe('What is EBITDA?');expect(body.grain).toBe('Month');expect(body.currency).toBe('AED');
});

test('sales overview follows period filters and provides compact comparison shortcuts',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Executive Dashboard',exact:true}).click();
  const format=value=>`AED ${new Intl.NumberFormat('en',{maximumFractionDigits:0}).format(value)}`;
  for(const period of ['ytd','qtd','day','mtd']){
    const response=page.waitForResponse(response=>{const url=new URL(response.url());return url.pathname==='/api/executive'&&url.searchParams.get('period')===period;});
    await page.getByLabel('Analysis period',{exact:true}).selectOption(period);
    const data=await(await response).json();
    await expect(page.locator('.headline-grid .metric-value').first()).toHaveText(format(data.analysis_revenue));
    await expect(page.locator('.executive-plan-grid article').first().locator('strong')).toHaveText(format(data.analysis_budget));
    await expect(page.locator('.executive-plan-panel')).toContainText(`${data.analysis_start} to ${data.analysis_end}`);
  }
  const bars=page.locator('.compact-plan-chart .recharts-bar-rectangle');await expect(bars).toHaveCount(3);
  const first=await bars.nth(0).boundingBox(),second=await bars.nth(1).boundingBox();
  expect(second.x-(first.x+first.width)).toBeGreaterThan(0);
  expect(second.x-(first.x+first.width)).toBeLessThan(first.width/2);
  await page.getByRole('navigation',{name:'Sales period and comparison shortcuts'}).getByRole('button',{name:'Last quarter',exact:true}).click();
  await expect(page.locator('.executive-plan-panel').getByText('Same time last quarter',{exact:true})).toBeVisible();
  await expect(page.locator('.executive-plan-panel').getByText('Same time last year',{exact:true})).toHaveCount(0);
  const request=page.waitForResponse(response=>{const url=new URL(response.url());return url.pathname==='/api/executive'&&url.searchParams.get('period')==='qtd';});
  await page.getByRole('navigation',{name:'Sales period and comparison shortcuts'}).getByRole('button',{name:'QTD',exact:true}).click();await request;
  await expect(page.getByLabel('Analysis period',{exact:true})).toHaveValue('qtd');
  await expect(page.getByRole('button',{name:'Ask Your Data',exact:true})).toHaveCount(0);
  await expect(page.getByText('Better Decisions.',{exact:true})).toHaveCount(0);
  await page.screenshot({path:'test-results/executive-period-controls.png',fullPage:true});
});

test('Operations assistant uses its own endpoint and selected report context',async({page})=>{
  let payload;
  await page.route('**/api/operations/chat',route=>{
    if(route.request().method()!=='POST')return route.continue();
    payload=route.request().postDataJSON();return route.fulfill({json:{answer:'Synthetic scrap rate is 3.8% [S1].',source_ids:['S1'],limitation:'',evidence:[{'Source ID':'S1',Metric:'Scrap Rate %',Value:3.8}]}});
  });
  await page.goto('/');await page.getByRole('button',{name:'Sustainability & Operations',exact:true}).click();
  const panel=page.getByRole('complementary',{name:'Operations Data side panel'});
  await expect(panel.getByRole('heading',{name:'Ask your Operations Data'})).toBeVisible();
  await expect(panel).toHaveCSS('background-color','rgb(11, 31, 51)');
  await panel.getByLabel('Question about Operations Data').fill('How is scrap rate performing?');
  await panel.getByRole('button',{name:'Ask',exact:true}).click();
  await expect(panel.getByText('Synthetic scrap rate is 3.8% [S1].')).toBeVisible();
  expect(payload.period).toBe('2026-12');expect(payload.grain).toBe('Month');
  await page.screenshot({path:'test-results/operations-scoped-sidebar.png',fullPage:true});
});

test('graph area outweighs compact shortcuts and operational cards sit side by side',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Executive Dashboard',exact:true}).click();
  const chart=page.locator('.compact-plan-chart'),controls=page.getByRole('navigation',{name:'Sales period and comparison shortcuts'});
  await expect(chart.locator('.recharts-bar-rectangle')).toHaveCount(3);
  const chartBox=await chart.boundingBox(),controlBox=await controls.boundingBox();expect(chartBox.width).toBeGreaterThan(300);
  for(const button of await controls.getByRole('button').all()){const box=await button.boundingBox();expect(box.width).toBeLessThan(235);expect(box.height).toBeGreaterThanOrEqual(47.25);expect(box.height).toBeLessThan(66);}
  await page.screenshot({path:'test-results/executive-compact-controls.png',fullPage:true});
  await page.getByRole('button',{name:'Sustainability & Operations',exact:true}).click();
  const cards=page.locator('.operations-stat-strip .operations-support-card');await expect(cards).toHaveCount(3);
  const boxes=await Promise.all([cards.nth(0).boundingBox(),cards.nth(1).boundingBox(),cards.nth(2).boundingBox()]);
  expect(Math.abs(boxes[0].y-boxes[1].y)).toBeLessThan(2);expect(Math.abs(boxes[1].y-boxes[2].y)).toBeLessThan(2);expect(boxes[2].x).toBeGreaterThan(boxes[1].x);
  await expect(cards.first().locator('.metric-comparisons')).toBeVisible();
  await cards.first().getByRole('button',{name:'View trend for Good Production'}).click();
  await expect(page.getByLabel('Operational trend metric')).toHaveValue('production_tonnes');
  await expect(page.getByRole('img',{name:'Good Production actual versus budget and forecast trend'})).toBeVisible();
  await page.screenshot({path:'test-results/operations-support-cards.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await expect(page.locator('.operations-stat-strip')).toHaveCSS('overflow-x','auto');
});

test('larger controls, wider left-anchored plan bars and horizontal rankings',async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Executive Dashboard',exact:true}).click();
  const plan=page.locator('.compact-plan-chart');const rects=plan.locator('.recharts-bar-rectangle .recharts-rectangle');
  await expect(rects).toHaveCount(3);
  const boxes=await Promise.all([rects.nth(0).boundingBox(),rects.nth(1).boundingBox(),rects.nth(2).boundingBox()]);
  const svg=await plan.locator('.recharts-surface').boundingBox();
  const slotWidth=(svg.width-118)/3;
  expect(Math.abs(boxes[0].width-slotWidth*0.8)).toBeLessThan(1.5);
  expect(Math.abs((boxes[1].x-boxes[0].x-boxes[0].width)-(12+slotWidth*0.2))).toBeLessThan(1.5);
  expect(Math.abs((boxes[2].x-boxes[1].x-boxes[1].width)-(12+slotWidth*0.2))).toBeLessThan(1.5);
  const axis=plan.locator('.recharts-yAxis .recharts-cartesian-axis-line');
  const axisX=Number(await axis.getAttribute('x1'));expect(Math.abs((Number(await rects.first().getAttribute('x'))-axisX)-(8+slotWidth*0.1))).toBeLessThan(1.5);
  const shortcuts=page.getByRole('navigation',{name:'Sales period and comparison shortcuts'});
  for(const button of await shortcuts.getByRole('button').all()){await expect(button).toHaveCSS('font-size','18.5625px');expect((await button.boundingBox()).height).toBeGreaterThanOrEqual(47.25);}
  await page.screenshot({path:'test-results/executive-larger-controls.png',fullPage:true});
  for(const [section,heading] of [['Customer performance','Top 10 customers by gross profit'],['Product performance','Top 10 SKUs by revenue']]){
    await page.getByRole('button',{name:section,exact:true}).click();
    const rankings=page.locator('.executive-ranking-grid .executive-ranking-visual');await expect(rankings).toHaveCount(2);
    await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible();
    for(const chart of await rankings.all()){const bar=await chart.locator('.recharts-bar-rectangle').last().boundingBox();expect(bar.width).toBeGreaterThan(bar.height);}
  }
  await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
});

const {test,expect}=require('@playwright/test');
const nav=page=>page.getByRole('navigation',{name:'Reporting & Analysis'});

test('three dashboards use sidebar filters and a common visual metric row',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.setViewportSize({width:1600,height:1050});await page.goto('/');
  for(const name of ['Financial Performance','Sustainability & Operations','Executive Dashboard']){
    await nav(page).getByRole('button',{name,exact:true}).click();
    const filters=page.locator('#reporting-sidebar-filters');
    await expect(filters.getByRole('heading',{name:'Reporting filters',exact:true})).toBeVisible();
    await expect(page.locator('main .filter-bar,main .executive-controls')).toHaveCount(0);
    const cards=page.locator('main .hero-metric');await expect(cards).toHaveCount(4);
    const boxes=await Promise.all([cards.nth(0).boundingBox(),cards.nth(1).boundingBox(),cards.nth(2).boundingBox(),cards.nth(3).boundingBox()]);
    expect(Math.max(...boxes.map(box=>box.y))-Math.min(...boxes.map(box=>box.y))).toBeLessThan(2);
    const filterBox=await filters.boundingBox(),navBox=await nav(page).boundingBox();expect(filterBox.y+filterBox.height).toBeLessThan(navBox.y);
    expect(await page.locator('main .page-description').isVisible()).toBeFalsy();
    if(name==='Executive Dashboard'){
      await expect(filters.getByLabel('Analysis period',{exact:true})).toHaveValue('mtd');
      await filters.getByLabel('Analysis period',{exact:true}).selectOption('ytd');
      await expect(cards.first()).toContainText('Year-to-date sales');
      await filters.getByLabel('Analysis period',{exact:true}).selectOption('mtd');
      await filters.getByLabel('Location',{exact:true}).selectOption('KSA');
      await expect(page.locator('.data-assistant-panel')).toContainText('KSA',{timeout:15000});
    }else{
      await expect(filters.getByLabel('Reporting View',{exact:true})).toHaveValue('Month');
      await expect(page.locator('.report-period-badge')).toContainText('Monthly source totals');
      await expect(page.locator('main .metric-sparkline').first()).toBeVisible();
    }
    await page.screenshot({path:`test-results/redesign-${name.split(' ')[0].toLowerCase()}.png`,fullPage:true});
  }
  expect(errors).toEqual([]);
});

test('sidebar filters work in the mobile drawer without horizontal overflow',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/');await expect(page.locator('main .hero-metric')).toHaveCount(4);
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await expect(page.getByLabel('Reporting View',{exact:true})).toBeVisible();
  await page.getByLabel('Reporting View',{exact:true}).selectOption('Quarter');
  await expect(page.getByLabel('Reporting Period',{exact:true})).toHaveValue('2026Q4');
  await nav(page).getByRole('button',{name:'Sustainability & Operations',exact:true}).click();
  await expect(page.getByRole('region',{name:'Operational headline metrics'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await nav(page).getByRole('button',{name:'Executive Dashboard',exact:true}).click();
  await expect(page.locator('main .hero-metric')).toHaveCount(4);
  await page.getByRole('button',{name:'Open navigation',exact:true}).click();
  await page.getByLabel('Analysis period',{exact:true}).selectOption('qtd');
  await expect(page.locator('main .hero-metric').first()).toContainText('Quarter-to-date sales');
  await page.getByRole('button',{name:'Close navigation',exact:true}).click({position:{x:370,y:100}});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/redesign-mobile.png',fullPage:true,animations:'disabled'});
});

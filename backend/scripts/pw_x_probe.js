const { chromium, firefox, webkit } = require('playwright');

(async () => {
  const targets = [
    ['chromium', chromium],
    ['firefox', firefox],
    ['webkit', webkit],
  ];
  for (const [name, browserType] of targets) {
    let browser;
    try {
      browser = await browserType.launch({ headless: true });
      const context = await browser.newContext();
      const page = await context.newPage();
      await page.goto('https://twitter.com/i/flow/login', { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(2500);
      const title = await page.title();
      const url = page.url();
      const body = await page.locator('body').innerText().catch(() => '');
      const hasUserInput = await page.locator('input[autocomplete="username"], input[name="text"]').first().isVisible().catch(() => false);
      const hasRetry = /something went wrong/i.test(body || '');
      const shot = `output/playwright/probe-${name}-${Date.now()}.png`;
      await page.screenshot({ path: shot, fullPage: true });
      console.log(JSON.stringify({name, ok:true, url, title, hasUserInput, hasRetry, shot}));
      await context.close();
    } catch (e) {
      console.log(JSON.stringify({name, ok:false, err:String(e)}));
    } finally {
      if (browser) await browser.close();
    }
  }
})();

const { firefox } = require('playwright');

(async () => {
  const user = process.env.TWITTER_USERNAME;
  const browser = await firefox.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto('https://twitter.com/i/flow/login', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2000);
  const input = page.locator('input[autocomplete="username"][name="text"]').first();
  await input.fill(user);
  await page.screenshot({ path: `output/playwright/step-probe-before-next-${Date.now()}.png`, fullPage: true });
  const next = page.getByRole('button', { name: /next/i }).first();
  await next.click();
  await page.waitForTimeout(4000);
  const url = page.url();
  const text = await page.locator('body').innerText();
  await page.screenshot({ path: `output/playwright/step-probe-after-next-${Date.now()}.png`, fullPage: true });
  console.log('URL=', url);
  console.log('BODY_SNIPPET=', text.replace(/\s+/g, ' ').slice(0, 800));
  await browser.close();
})();

const { test, expect } = require('/home/kxyx/.config/nvm/versions/node/v24.13.0/lib/node_modules/@playwright/test');

test('seed', async ({ page }) => {
  await page.goto('http://localhost:3000');
});

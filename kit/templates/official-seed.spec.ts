import { test, expect } from './fixtures';

test('Authoring seed: authenticated browser only', async ({ page }) => {
  await expect(page.locator('body')).toBeVisible();
  await page.pause();
});

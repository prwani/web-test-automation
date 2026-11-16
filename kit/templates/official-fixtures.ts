import { test as base, expect } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

type Login = null | {
  username: string; password: string; submit: string; authenticated: string;
  requests?: { method: string; path: string }[];
};
const baseURL = process.env.APP_BASE_URL;
if (!baseURL || baseURL !== process.env.APP_APPROVED_BASE_URL) throw new Error('Approved target required');
const origin = new URL(baseURL).origin;
const login: Login = JSON.parse(fs.readFileSync(path.join(__dirname, 'login.json'), 'utf8'));

export const test = base.extend({
  page: async ({ page, context }, use, testInfo) => {
    let loggingIn = false;
    await context.route('**/*', async route => {
      const request = route.request();
      const url = new URL(request.url());
      const safe = ['GET', 'HEAD', 'OPTIONS'].includes(request.method());
      const authentication = loggingIn && login?.requests?.some(
        entry => entry.method === request.method() && entry.path === url.pathname + url.search);
      if (url.origin !== origin || (!safe && !authentication)) return route.abort();
      return route.continue();
    });
    await page.goto(baseURL);
    if (login) {
      const username = process.env.APP_USERNAME, password = process.env.APP_PASSWORD;
      if (!username || !password) throw new Error('Simple login requires APP_USERNAME and APP_PASSWORD; interactive SSO is unsupported');
      const passwordInput = page.locator(login.password);
      if (await passwordInput.getAttribute('type') !== 'password') throw new Error('Login password target must have type=password');
      await page.locator(login.username).fill(username);
      await passwordInput.fill(password);
      try {
        loggingIn = true;
        await page.locator(login.submit).click();
        await expect(page.locator(login.authenticated)).toBeVisible();
      } finally {
        loggingIn = false;
      }
    }
    if (new URL(page.url()).origin !== origin) throw new Error('Authentication left the approved origin');
    const evidence = process.env.APP_EVIDENCE === '1' && process.env.APP_SEED !== '1';
    if (evidence) await context.tracing.start({ screenshots: true, snapshots: true });
    try {
      await use(page);
    } finally {
      if (evidence) {
        try {
          const name = testInfo.status !== testInfo.expectedStatus ? 'failure.png' : 'outcome.png';
          await page.screenshot({ path: testInfo.outputPath(name), fullPage: true });
        } finally {
          await context.tracing.stop({ path: testInfo.outputPath('trace.zip') });
        }
      }
    }
  },
});
export { expect };

const { test, expect } = require('@playwright/test');

function baseURL() {
  if (!process.env.CRM_BASE_URL) throw new Error('CRM_BASE_URL is required for the authorized test environment');
  const url = new URL(process.env.CRM_BASE_URL);
  if (!process.env.CRM_APPROVED_BASE_URL || url.href !== new URL(process.env.CRM_APPROVED_BASE_URL).href) {
    throw new Error('Runtime CRM URL differs from the source mapping approved for this execution');
  }
  if (url.username || url.password || url.search || url.hash ||
      (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)))) {
    throw new Error('CRM_BASE_URL must use HTTPS (or loopback HTTP) without credentials, query or fragment');
  }
  return url;
}

function value(input) {
  return input.replace(/\{\{([A-Z][A-Z0-9_]*)\}\}/g, (_, key) => {
    const name = `CRM_DATA_${key}`;
    if (process.env[name] === undefined) throw new Error(`Missing controlled test-data environment variable ${name}`);
    return process.env[name];
  });
}

function locator(page, target) {
  switch (target.by) {
    case 'css': return page.locator(value(target.value));
    case 'role': return page.getByRole(target.value, { name: value(target.name), exact: true });
    case 'label': return page.getByLabel(value(target.value), { exact: true });
    case 'text': return page.getByText(value(target.value), { exact: true });
    default: throw new Error('Unsupported reviewed locator');
  }
}

async function step(page, operation) {
  const action = operation.action;
  if (action === 'goto') {
    const destination = new URL(operation.path, baseURL());
    if (destination.origin !== baseURL().origin || destination.username || destination.password) throw new Error('Navigation outside approved CRM origin');
    await page.goto(destination.href);
  } else {
    const target = locator(page, operation.target);
    switch (action) {
      case 'click': await target.click(); break;
      case 'fill':
        if ((await target.getAttribute('type'))?.toLowerCase() === 'password') throw new Error('Plan cannot fill passwords; use configured login');
        await target.fill(value(operation.value)); break;
      case 'press': await target.press(operation.value); break;
      case 'expectVisible': await expect(target).toBeVisible(); break;
      case 'expectAbsent': await expect(target).toHaveCount(0); break;
      case 'expectText': await expect(target).toHaveText(value(operation.value)); break;
      case 'expectValue': await expect(target).toHaveValue(value(operation.value)); break;
      case 'expectCount': await expect(target).toHaveCount(operation.value); break;
      default: throw new Error('Unsupported compiled action');
    }
  }
  if (new URL(page.url()).origin !== baseURL().origin) throw new Error('Browser left the approved CRM origin');
}

function defineTests(plan, cases) {
  const selected = JSON.parse(process.env.CRM_CASE_IDS || '[]');
  if (!Array.isArray(selected) || selected.length === 0) throw new Error('Use automation.py run so source mappings and case selection are verified');
  test.beforeEach(async ({ page }) => {
    await page.goto(baseURL().href);
    if (plan.login) {
      if (!process.env.CRM_USERNAME || !process.env.CRM_PASSWORD) throw new Error('CRM_USERNAME and CRM_PASSWORD must be supplied locally for configured test login');
      const password = locator(page, plan.login.password);
      if ((await password.getAttribute('type'))?.toLowerCase() !== 'password') throw new Error('Login password target must be an actual password input');
      await locator(page, plan.login.username).fill(process.env.CRM_USERNAME);
      await password.fill(process.env.CRM_PASSWORD);
      await locator(page, plan.login.submit).click();
      await expect(locator(page, plan.login.authenticated)).toBeVisible();
    }
    if (new URL(page.url()).origin !== baseURL().origin) throw new Error('Complete approved authentication setup before execution; no cross-origin login bypass');
  });
  for (const source of cases) {
    if (!selected.includes(source.id)) continue;
    const mapped = plan.cases.find(c => c.caseId === source.id);
    test(`${source.id} | ${source.title}`, async ({ page, context }, info) => {
      info.annotations.push({ type: 'source-case-id', description: source.id });
      for (const id of source.requirementRefs) info.annotations.push({ type: 'requirement', description: id });
      for (const id of source.observationRefs) info.annotations.push({ type: 'ui-observation', description: id });
      const evidence = process.env.CRM_EVIDENCE === '1';
      if (evidence) await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
      try {
        for (let i = 0; i < mapped.steps.length; i++) {
          await test.step(`${source.id} step ${i + 1}: ${mapped.steps[i].action}`, () => step(page, mapped.steps[i]));
        }
      } finally {
        if (evidence) {
          await context.tracing.stop({ path: info.outputPath('authenticated-workflow-trace.zip') });
          await page.screenshot({ path: info.outputPath('outcome.png'), fullPage: true });
        }
      }
    });
  }
}

module.exports = { defineTests };

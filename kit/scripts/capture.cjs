const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline/promises');
const { chromium, expect } = require('@playwright/test');
const { validateBrief, loadBrief } = require('./explore.cjs');

function options(args) {
  const result = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--allow-ui-actions' || args[i] === '--headless') result[args[i].slice(2)] = true;
    else if (['--config', '--out', '--url', '--prompt', '--prompt-file'].includes(args[i])) {
      if (!args[i + 1] || args[i + 1].startsWith('--')) throw new Error(`Missing value for ${args[i]}`);
      result[args[i].slice(2)] = args[++i];
    } else throw new Error(`Unknown option ${args[i]}`);
  }
  if (!result.out || (!result.config && !result.url)) throw new Error('Usage: node scripts\\capture.cjs (--config PATH | --url URL --prompt TEXT) --out PATH');
  if (result.prompt && result['prompt-file']) throw new Error('Choose --prompt or --prompt-file, not both');
  if (result.config && (result.url || result.prompt || result['prompt-file'])) throw new Error('Use config OR URL/prompt input, not both');
  if (!result.config && Number(!!result.prompt) + Number(!!result['prompt-file']) !== 1) throw new Error('URL-based capture requires --prompt or --prompt-file');
  return result;
}

function configFor(args) {
  if (args.config) return JSON.parse(fs.readFileSync(args.config, 'utf8').replace(/^\uFEFF/, ''));
  const brief = loadBrief(args);
  return {
    url: brief.url, scope: brief.scope, captureSelector: 'body', authenticatedSelector: 'body',
    requireManualAuthConfirmation: true, steps: [],
  };
}

async function capture(config, args) {
  const url = new URL(config.url);
  if (url.username || url.password || url.search || url.hash) throw new Error('Use an origin/path URL without credentials, query or fragment');
  if (url.protocol !== 'https:' && !(url.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname))) {
    throw new Error('HTTPS required except for a local encrypted-tunnel endpoint');
  }
  if (!config.scope || !config.captureSelector || !config.authenticatedSelector) throw new Error('Scope, captureSelector and authenticatedSelector required');
  validateBrief(config.url, config.scope);
  if (config.steps?.length && !args['allow-ui-actions']) throw new Error('Configured UI actions require explicit --allow-ui-actions');
  if (args.headless && !config.login) throw new Error('Headless capture requires configured environment-variable login; use headed capture for SSO/MFA');
  if (config.requireManualAuthConfirmation && (args.headless || config.login || config.steps?.length)) {
    throw new Error('Prompt-guided capture requires headed human login and manual checkpoints; use an explicit configured flow for automation');
  }
  const output = path.resolve(args.out);
  if (fs.existsSync(output)) throw new Error('Output already exists; choose a fresh capture path');
  const browser = await chromium.launch({ headless: !!args.headless });
  const terminal = readline.createInterface({ input: process.stdin, output: process.stdout });
  const observations = [];
  try {
    const page = await browser.newPage();
    await page.goto(config.url);
    if (config.login) {
      const login = config.login;
      const username = process.env[login.usernameEnv];
      const password = process.env[login.passwordEnv];
      if (!username || !password) throw new Error('Configured login environment variables are missing');
      await page.locator(login.usernameSelector).fill(username);
      await page.locator(login.passwordSelector).fill(password);
      await page.locator(login.submitSelector).click();
    } else {
      console.log(`FEATURES AND NAVIGATION BRIEF:\n${config.scope}\n`);
      if (config.requireManualAuthConfirmation) {
        const answer = await terminal.question('Sign in yourself (including SSO/MFA), open the approved feature, and type SIGNED IN to confirm. ');
        if (answer.trim() !== 'SIGNED IN') throw new Error('Manual authenticated-page confirmation was not supplied; nothing captured');
      } else {
        await terminal.question('Sign in manually in the browser (including SSO/MFA), open the authorized feature, then press Enter. ');
      }
    }
    await expect(page.locator(config.authenticatedSelector)).toBeVisible({ timeout: 60_000 });
    const actions = [];
    async function snapshot(title, outcome) {
      const target = page.locator(config.captureSelector);
      await expect(target).toBeVisible();
      observations.push({
        id: `UI-${String(observations.length + 1).padStart(3, '0')}`,
        title, actions: [...actions], outcome,
        evidence: await target.ariaSnapshot(),
      });
    }
    if (config.steps?.length) {
      for (const step of config.steps) {
        const locator = step.selector ? page.locator(step.selector) : null;
        switch (step.action) {
          case 'click':
            await locator.click();
            actions.push(`Click ${step.selector}`);
            break;
          case 'fill':
            if (await locator.getAttribute('type') === 'password') throw new Error('Password fields are forbidden after authentication');
            await locator.fill(step.value);
            actions.push(`Fill ${step.selector} with ${step.value}`);
            break;
          case 'press':
            await locator.press(step.key);
            actions.push(`Press ${step.key} in ${step.selector}`);
            break;
          case 'visible':
            await expect(locator).toBeVisible();
            break;
          case 'absent':
            await expect(locator).toHaveCount(0);
            break;
          case 'snapshot':
            if (!step.title || !step.outcome) throw new Error('Snapshots require title and observed outcome');
            await snapshot(step.title, step.outcome);
            break;
          default: throw new Error(`Unsupported action ${step.action}`);
        }
      }
    } else {
      while (true) {
        const title = await terminal.question('Follow the feature/navigation brief. Enter "Feature: checkpoint" (empty finishes): ');
        if (!title.trim()) break;
        const action = await terminal.question('Describe the actions you actually performed (no credentials/PII): ');
        const outcome = await terminal.question('Describe the outcome actually observed: ');
        if (!action.trim() || !outcome.trim()) throw new Error('Checkpoint actions and outcome cannot be empty');
        actions.push(action);
        await snapshot(title, outcome);
      }
    }
    if (!observations.length) throw new Error('No observations captured');
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, JSON.stringify({
      schemaVersion: 1, scope: config.scope, reviewed: false,
      provenance: { method: 'Playwright live browser capture', capturedAt: new Date().toISOString() },
      observations,
    }, null, 2), { flag: 'wx', mode: 0o600 });
    console.log(`Captured ${observations.length} checkpoints. PRIVATE RAW DATA: sanitize and explicitly review before AI processing.`);
  } finally {
    terminal.close();
    await browser.close();
  }
}

if (require.main === module) {
  Promise.resolve().then(() => {
    const args = options(process.argv.slice(2));
    return capture(configFor(args), args);
  }).catch(error => {
    console.error(`Capture failed: ${error.message}`);
    process.exitCode = 1;
  });
}
module.exports = { options, capture, configFor };

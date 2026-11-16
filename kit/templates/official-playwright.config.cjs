const path = require('node:path');
const selected = JSON.parse(process.env.APP_SELECTED_SPECS || '[]');
const seed = process.env.APP_SEED === '1';
if (!process.env.APP_RUN_DIR || (!seed && !selected.length)) throw new Error('Use official.py run for mapped execution');
module.exports = {
  testDir: __dirname,
  testMatch: seed ? ['seed.spec.ts'] : selected,
  forbidOnly: true, retries: 0, workers: 1, fullyParallel: false, repeatEach: 1,
  timeout: 45000, expect: { timeout: 10000 },
  outputDir: path.join(process.env.APP_RUN_DIR, 'artifacts'),
  reporter: [
    ['json', { outputFile: path.join(process.env.APP_RUN_DIR, 'playwright-results.json') }],
    ['html', { outputFolder: path.join(process.env.APP_RUN_DIR, 'html'), open: 'never' }],
  ],
  use: { browserName: 'chromium', headless: process.env.APP_HEADED !== '1', trace: 'off', screenshot: 'off', video: 'off' },
};

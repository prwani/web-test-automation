const path = require('node:path');
if (!process.env.CRM_RUN_DIR) throw new Error('Use automation.py run for mapped execution');
module.exports = {
  testDir: path.join(__dirname, 'tests'),
  testMatch: '**/*.spec.cjs',
  forbidOnly: true, retries: 0, workers: 1, fullyParallel: false, repeatEach: 1,
  timeout: 45000, expect: { timeout: 10000 },
  outputDir: path.join(process.env.CRM_RUN_DIR, 'artifacts'),
  reporter: [
    ['json', { outputFile: path.join(process.env.CRM_RUN_DIR, 'playwright-results.json') }],
    ['html', { outputFolder: path.join(process.env.CRM_RUN_DIR, 'html'), open: 'never' }],
  ],
  use: {
    browserName: 'chromium', headless: process.env.CRM_HEADED !== '1',
    trace: 'off', screenshot: 'off', video: 'off',
  },
};

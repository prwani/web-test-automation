const path = require('node:path');
function envValue(suffix) {
  const app = process.env[`APP_${suffix}`], legacy = process.env[`CRM_${suffix}`];
  if (app !== undefined && legacy !== undefined && app !== legacy) throw new Error(`Conflicting APP_${suffix} and CRM_${suffix} environment variables`);
  return app ?? legacy;
}
const runDir = envValue('RUN_DIR');
if (!runDir) throw new Error('Use automation.py run for mapped execution');
module.exports = {
  testDir: path.join(__dirname, 'tests'),
  testMatch: '**/*.spec.cjs',
  forbidOnly: true, retries: 0, workers: 1, fullyParallel: false, repeatEach: 1,
  timeout: 45000, expect: { timeout: 10000 },
  outputDir: path.join(runDir, 'artifacts'),
  reporter: [
    ['json', { outputFile: path.join(runDir, 'playwright-results.json') }],
    ['html', { outputFolder: path.join(runDir, 'html'), open: 'never' }],
  ],
  use: {
    browserName: 'chromium', headless: envValue('HEADED') !== '1',
    trace: 'off', screenshot: 'off', video: 'off',
  },
};

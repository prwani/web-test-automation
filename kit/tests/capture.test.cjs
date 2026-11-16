const { test } = require('node:test');
const assert = require('node:assert/strict');
const { capture, options } = require('../scripts/capture.cjs');

const config = {
  url: 'https://example.invalid',
  scope: 'Customer search',
  captureSelector: 'main',
  authenticatedSelector: 'main',
};

test('capture requires explicit config and fresh output arguments', () => {
  assert.throws(() => options([]), /Usage/);
  assert.throws(() => options(['--config']), /Missing value/);
  assert.throws(() => options(['--anything']), /Unknown option/);
  assert.deepEqual(options(['--config', 'config.json', '--out', 'out.json', '--headless']), {
    config: 'config.json', out: 'out.json', headless: true,
  });
});

test('capture refuses remote plain HTTP before opening browser', async () => {
  await assert.rejects(capture({ ...config, url: 'http://example.invalid' }, { out: 'unused.json' }), /HTTPS/);
});

test('capture refuses credentials and query tokens in URL', async () => {
  for (const url of ['https://user:password@example.invalid', 'https://example.invalid?token=redacted', 'https://example.invalid#secret']) {
    await assert.rejects(capture({ ...config, url }, { out: 'unused.json' }), /credentials, query or fragment/);
  }
});

test('configured actions require operator authorization', async () => {
  await assert.rejects(capture({ ...config, steps: [{ action: 'click', selector: 'button' }] }, { out: 'unused.json' }), /allow-ui-actions/);
});

test('headless capture cannot pretend to handle manual SSO', async () => {
  await assert.rejects(capture(config, { out: 'unused.json', headless: true }), /Headless capture requires/);
});

test('capture scope and selectors cannot be omitted', async () => {
  await assert.rejects(capture({ url: config.url }, { out: 'unused.json' }), /required/);
});

test('capture prompt route is explicit and cannot be mixed with scripted config', () => {
  assert.equal(options(['--url', config.url, '--prompt', 'Explore search', '--out', 'out.json']).prompt, 'Explore search');
  assert.throws(() => options(['--url', config.url, '--out', 'out.json']), /requires/);
  assert.throws(() => options(['--config', 'config.json', '--prompt', 'Search', '--out', 'out.json']), /not both/);
});

test('prompt-guided capture cannot silently run configured or headless actions', async () => {
  await assert.rejects(capture({
    ...config, requireManualAuthConfirmation: true,
    login: { usernameEnv: 'UNUSED_USER', passwordEnv: 'UNUSED_PASS' },
  }, { out: 'unused.json', headless: true }), /headed human login/);
});

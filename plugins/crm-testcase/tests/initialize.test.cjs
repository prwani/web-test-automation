const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { initialize, options } = require('../skills/crm-testcase/scripts/initialize.cjs');

function fixture(run) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'crm-plugin-init-'));
  const plugin = path.join(directory, 'plugin');
  const kit = path.join(plugin, 'skills', 'crm-testcase', 'kit');
  fs.mkdirSync(kit, { recursive: true });
  fs.writeFileSync(path.join(plugin, 'plugin.json'), '{"name":"crm-testcase","version":"1.0.0"}');
  const content = 'An allowlisted code asset, not a credential.\n';
  fs.writeFileSync(path.join(kit, 'README.md'), content);
  const manifest = {
    schemaVersion: 1, package: 'CRM-Testcase-Customer-Kit', version: '1.1.0',
    files: { 'README.md': crypto.createHash('sha256').update(content).digest('hex') },
  };
  const manifestPath = path.join(kit, 'MANIFEST.json');
  fs.writeFileSync(manifestPath, JSON.stringify(manifest));
  try { run({ directory, plugin, kit, manifest, manifestPath }); }
  finally { fs.rmSync(directory, { recursive: true }); }
}

test('initializer creates a verified fresh customer workspace without copying unlisted data', () => fixture(({ directory, plugin, kit }) => {
  fs.writeFileSync(path.join(kit, 'unlisted.private'), 'must not copy');
  const target = path.join(directory, 'work', 'search');
  const result = initialize(target, plugin);
  assert.equal(result.count, 1);
  assert.equal(result.kitVersion, '1.1.0');
  assert.deepEqual(fs.readdirSync(target).sort(), ['.crm-testcase-workspace.json', 'MANIFEST.json', 'README.md'].sort());
  const marker = JSON.parse(fs.readFileSync(path.join(target, '.crm-testcase-workspace.json'), 'utf8'));
  assert.equal(marker.plugin, 'crm-testcase');
  assert.equal(marker.kitVersion, '1.1.0');
  assert.equal(fs.existsSync(path.join(target, 'node_modules')), false);
  assert.equal(fs.existsSync(path.join(target, '.local')), false);
}));

test('initializer refuses existing workspace without altering customer files', () => fixture(({ directory, plugin }) => {
  const target = path.join(directory, 'work');
  fs.mkdirSync(target);
  fs.writeFileSync(path.join(target, 'customer.txt'), 'preserve');
  assert.throws(() => initialize(target, plugin), /already exists/);
  assert.equal(fs.readFileSync(path.join(target, 'customer.txt'), 'utf8'), 'preserve');
}));

test('initializer refuses writes inside plugin installation', () => fixture(({ plugin }) => {
  assert.throws(() => initialize(path.join(plugin, 'runs'), plugin), /outside/);
  assert.equal(fs.existsSync(path.join(plugin, 'runs')), false);
}));

test('initializer verifies every file before creating workspace', () => fixture(({ directory, plugin, kit }) => {
  fs.writeFileSync(path.join(kit, 'README.md'), 'tampered');
  const target = path.join(directory, 'work');
  assert.throws(() => initialize(target, plugin), /differs/);
  assert.equal(fs.existsSync(target), false);
}));

test('initializer rejects traversal, private-output paths and reserved files', () => fixture(({ directory, plugin, manifest, manifestPath }) => {
  for (const name of ['../outside', '/absolute', 'C:/absolute', 'a\\b', '.local/secret', 'runs/old.json',
    'node_modules/pkg', '.venv/config', 'a/../b', 'MANIFEST.json', '.crm-testcase-workspace.json']) {
    manifest.files = { [name]: 'a'.repeat(64) };
    fs.writeFileSync(manifestPath, JSON.stringify(manifest));
    const target = path.join(directory, 'work');
    assert.throws(() => initialize(target, plugin), /Unsafe/);
    assert.equal(fs.existsSync(target), false);
  }
}));

test('initializer requires a deliberate workspace argument', () => {
  for (const args of [[], ['--workspace'], ['--workspace', '--overwrite'], ['--other', 'folder']]) {
    assert.throws(() => options(args), /Usage/);
  }
  assert.equal(options(['--workspace', 'approved-folder']), 'approved-folder');
});

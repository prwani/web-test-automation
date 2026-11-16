const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const kit = path.resolve(__dirname, '..');
const script = path.join(kit, 'scripts', 'playwright-skill.cjs');

test('official skill setup is explicit, isolated, verified and refuses replacement', () => {
  const local = path.join(kit, '.local');
  fs.mkdirSync(local, { recursive: true });
  const root = fs.mkdtempSync(path.join(local, 'skill-test-'));
  const run = (...args) => spawnSync(process.execPath, [script, ...args, '--workspace', root], { encoding: 'utf8' });
  try {
    fs.writeFileSync(path.join(root, '.web-test-workspace.json'), JSON.stringify({ schemaVersion: 1, plugin: 'web-test' }));
    const other = path.join(root, '.agents', 'skills', 'other');
    fs.mkdirSync(other, { recursive: true });
    fs.writeFileSync(path.join(other, 'draft.md'), 'keep');
    assert.notEqual(run('check').status, 0);
    assert.notEqual(run('setup').status, 0);
    assert.equal(fs.existsSync(path.join(root, '.agents', 'skills', 'playwright-cli')), false);
    const installed = run('setup', '--confirm-install-skills');
    assert.equal(installed.status, 0, installed.stderr);
    assert.equal(run('check').status, 0);
    assert.equal(fs.readFileSync(path.join(other, 'draft.md'), 'utf8'), 'keep');
    assert.equal(fs.existsSync(path.join(root, '.playwright')), false);
    assert.equal(fs.readdirSync(path.join(root, '.local')).some(name => name.startsWith('playwright-skill-stage-')), false);
    assert.notEqual(run('setup', '--confirm-install-skills').status, 0);
    const skill = path.join(root, '.agents', 'skills', 'playwright-cli', 'SKILL.md');
    fs.appendFileSync(skill, '\nlocal draft');
    assert.notEqual(run('check').status, 0);
    assert.notEqual(run('setup', '--confirm-install-skills').status, 0);
    assert.match(fs.readFileSync(skill, 'utf8'), /local draft/);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test('setup rejects folders without the workspace marker', () => {
  const result = spawnSync(process.execPath, [script, 'setup', '--confirm-install-skills', '--workspace', kit], { encoding: 'utf8' });
  assert.notEqual(result.status, 0);
});

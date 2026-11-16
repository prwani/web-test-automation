const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { options, validateBrief, loadBrief, prepare } = require('../scripts/explore.cjs');
const { configFor } = require('../scripts/capture.cjs');

test('natural-language features and optional navigation survive preparation unchanged', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'web-prompt-'));
  try {
    const prompt = 'Explore item search and clearing search. Navigation: main menu > Items. Do not edit records.';
    const brief = validateBrief('https://app.example.invalid', prompt);
    const out = prepare(brief, path.join(directory, 'task'));
    const request = JSON.parse(fs.readFileSync(path.join(out, 'exploration-request.json'), 'utf8'));
    assert.equal(request.scope, prompt);
    assert.equal(request.status, 'Prepared - no browser exploration performed');
    assert.equal(request.limits.recordMutationAllowed, false);
    assert.equal(request.observationSchema.reviewed, false);
    assert.match(fs.readFileSync(path.join(out, 'agent-task.txt'), 'utf8'), /Navigation: main menu > Items/);
    assert.match(fs.readFileSync(path.join(out, 'agent-task.txt'), 'utf8'), /No create\/edit\/delete/);
    assert.equal(fs.existsSync(path.join(out, 'observations.raw.json')), false);
    assert.throws(() => prepare(brief, out), /already exists/);
  } finally {
    fs.rmSync(directory, { recursive: true });
  }
});

test('feature prompt without navigation hints is valid and needs no guessed selectors', () => {
  const config = configFor({ url: 'https://app.example.invalid', prompt: 'Explore item search' });
  assert.equal(config.scope, 'Explore item search');
  assert.equal(config.captureSelector, 'body');
  assert.equal(config.requireManualAuthConfirmation, true);
  assert.deepEqual(config.steps, []);
});

test('prompt-file supports multiline feature/navigation text with UTF-8 BOM', () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'web-prompt-file-'));
  try {
    const file = path.join(directory, 'prompt.txt');
    fs.writeFileSync(file, '\uFEFFExplore item search.\nNavigation: Items > list.\n');
    const args = options(['--url', 'https://app.example.invalid', '--prompt-file', file, '--out', 'unused']);
    assert.equal(loadBrief(args).scope, 'Explore item search.\nNavigation: Items > list.');
  } finally {
    fs.rmSync(directory, { recursive: true });
  }
});

test('ambiguous prompt sources, missing fields and duplicate values are rejected', () => {
  for (const args of [
    [], ['--url', 'https://example.invalid', '--out', 'task'],
    ['--url', 'https://example.invalid', '--prompt', 'One', '--prompt-file', 'two', '--out', 'task'],
    ['--url', 'https://example.invalid', '--prompt', 'One', '--prompt', 'Two', '--out', 'task'],
  ]) assert.throws(() => options(args));
});

test('empty, oversized and control-character briefs are rejected', () => {
  for (const value of ['', '  ', 'a'.repeat(20001), 'search\x00secret']) {
    assert.throws(() => validateBrief('https://app.example.invalid', value), /Feature prompt/);
  }
});

test('URL boundaries reject remote HTTP and embedded credentials or tokens', () => {
  for (const url of ['http://example.invalid', 'https://u:p@example.invalid', 'https://example.invalid?t=secret', 'https://example.invalid#secret']) {
    assert.throws(() => validateBrief(url, 'Item search'));
  }
  assert.equal(validateBrief('http://127.0.0.1:8080', 'Search').url, 'http://127.0.0.1:8080/');
});

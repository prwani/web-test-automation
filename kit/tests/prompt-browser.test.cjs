const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawn } = require('node:child_process');

test('prompt-only headed capture records real local UI after operator confirmation', { timeout: 90000 }, async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'web-prompt-browser-'));
  const server = http.createServer((request, response) => {
    response.writeHead(200, { 'Content-Type': 'text/html' });
    response.end('<!doctype html><title>Controlled capture fixture</title><main><h1>Item search</h1><label>Search <input name="search"></label><p>ITEM_A</p></main>');
  });
  let child;
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    const url = `http://127.0.0.1:${server.address().port}`;
    const prompt = 'Explore item search and clearing search. Navigation: main page > Item search.';
    const output = path.join(directory, 'observations.raw.json');
    const interactions = [
      ['type SIGNED IN', 'SIGNED IN'],
      ['Enter "Feature: checkpoint"', 'Item search: initial page'],
      ['Describe the actions', 'Open the authorized local fixture'],
      ['Describe the outcome', 'Item search heading and ITEM_A are visible'],
      ['Enter "Feature: checkpoint"', ''],
    ];
    child = spawn(process.execPath, [
      path.join(__dirname, '..', 'scripts', 'capture.cjs'),
      '--url', url, '--prompt', prompt, '--out', output,
    ], { stdio: ['pipe', 'pipe', 'pipe'] });
    let transcript = '';
    let pending = '';
    let index = 0;
    child.stdout.on('data', chunk => {
      transcript += chunk;
      pending += chunk;
      if (index < interactions.length && pending.includes(interactions[index][0])) {
        child.stdin.write(interactions[index][1] + '\n');
        index++;
        pending = '';
      }
    });
    child.stderr.on('data', chunk => { transcript += chunk; });
    const code = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        child.kill();
        reject(new Error(`Prompt browser interaction timed out at ${index}: ${transcript}`));
      }, 75000);
      child.once('error', error => { clearTimeout(timer); reject(error); });
      child.once('exit', result => { clearTimeout(timer); resolve(result); });
    });
    assert.equal(code, 0, transcript);
    assert.equal(index, interactions.length);
    const capture = JSON.parse(fs.readFileSync(output, 'utf8'));
    assert.equal(capture.scope, prompt);
    assert.equal(capture.reviewed, false);
    assert.equal(capture.observations.length, 1);
    assert.equal(capture.observations[0].title, 'Item search: initial page');
    assert.match(capture.observations[0].evidence, /Item search/);
    assert.match(capture.observations[0].evidence, /ITEM_A/);
    assert.equal(capture.provenance.method, 'Playwright live browser capture');
  } finally {
    if (child && child.exitCode === null) child.kill();
    await new Promise(resolve => server.close(resolve));
    fs.rmSync(directory, { recursive: true });
  }
});

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { createRequire } = require('node:module');

const CLI_VERSION = '0.1.23';
const TEST_VERSION = '1.64.1';
const CORE_VERSION = '1.65.0-alpha-2026-10-30';
const kit = path.resolve(__dirname, '..');

function hash(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function tree(dir, prefix = '') {
  const result = {};
  for (const entry of fs.readdirSync(path.join(dir, prefix), { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
    const name = path.join(prefix, entry.name);
    if (entry.isDirectory()) Object.assign(result, tree(dir, name));
    else if (entry.isFile()) result[name.split(path.sep).join('/')] = hash(path.join(dir, name));
    else throw new Error('Skill contains a symlink or unsupported file');
  }
  return result;
}

function safePath(root, relative) {
  let current = root;
  for (const part of relative.split(path.sep)) {
    current = path.join(current, part);
    try {
      if (fs.lstatSync(current).isSymbolicLink()) throw new Error(`Symlink not allowed: ${relative}`);
    } catch (error) {
      if (error.code !== 'ENOENT') throw error;
    }
  }
  return current;
}

function workspace(value) {
  const root = fs.realpathSync(value);
  const marker = safePath(root, '.web-test-workspace.json');
  const info = JSON.parse(fs.readFileSync(marker, 'utf8'));
  if (info.schemaVersion !== 1 || info.plugin !== 'web-test') throw new Error('Not an initialized web-test workspace');
  const scriptRoot = fs.realpathSync(kit);
  const scriptInPlugin = scriptRoot.toLowerCase().includes(`${path.sep}skills${path.sep}web-test${path.sep}kit`.toLowerCase());
  if (scriptInPlugin) throw new Error('Run the helper from the initialized workspace, not a plugin bundle');
  if (root === scriptRoot && fs.existsSync(path.join(root, '..', '.git'))) {
    throw new Error('Refusing to install in the source kit');
  }
  if (root.toLowerCase().includes(`${path.sep}skills${path.sep}web-test${path.sep}kit`.toLowerCase())) {
    throw new Error('Workspace must be outside the plugin bundle');
  }
  return root;
}

function toolchain() {
  const cliJson = require.resolve('@playwright/cli/package.json', { paths: [kit] });
  const testJson = require.resolve('@playwright/test/package.json', { paths: [kit] });
  const cliRequire = createRequire(cliJson);
  const coreJson = cliRequire.resolve('playwright-core/package.json');
  const playwrightJson = cliRequire.resolve('playwright/package.json');
  const cli = JSON.parse(fs.readFileSync(cliJson, 'utf8'));
  const test = JSON.parse(fs.readFileSync(testJson, 'utf8'));
  const core = JSON.parse(fs.readFileSync(coreJson, 'utf8'));
  const playwright = JSON.parse(fs.readFileSync(playwrightJson, 'utf8'));
  if (cli.version !== CLI_VERSION || test.version !== TEST_VERSION || core.version !== CORE_VERSION || playwright.version !== CORE_VERSION ||
      cli.bin?.['playwright-cli'] !== 'playwright-cli.js') throw new Error('Installed Playwright toolchain does not match pinned versions');
  const bin = path.join(path.dirname(cliJson), cli.bin['playwright-cli']);
  const source = path.join(path.dirname(coreJson), 'lib', 'tools', 'skills', 'playwright-cli');
  const files = tree(source);
  if (!files['SKILL.md'] || !files['references/test-generation.md']) throw new Error('Official skill or test-generation reference missing from package');
  return { bin, files, versions: { cli: cli.version, test: test.version, cliPlaywright: playwright.version, cliCore: core.version },
    hashes: { cliPackage: hash(cliJson), cliBin: hash(bin), testPackage: hash(testJson),
      testBin: hash(path.join(path.dirname(testJson), 'cli.js')),
      corePackage: hash(coreJson), coreBundle: hash(path.join(path.dirname(coreJson), 'lib', 'coreBundle.js')),
      playwrightPackage: hash(playwrightJson) } };
}

function check(root, tools) {
  const dest = safePath(root, path.join('.agents', 'skills', 'playwright-cli'));
  const receiptPath = safePath(root, path.join('.local', 'playwright-skill-receipt.json'));
  const receipt = JSON.parse(fs.readFileSync(receiptPath, 'utf8'));
  if (JSON.stringify(tree(dest)) !== JSON.stringify(tools.files) ||
      JSON.stringify(receipt.skillFiles) !== JSON.stringify(tools.files) ||
      JSON.stringify(receipt.versions) !== JSON.stringify(tools.versions) ||
      JSON.stringify(receipt.toolchainHashes) !== JSON.stringify(tools.hashes)) {
    throw new Error('Installed skill or toolchain differs from the pinned package/receipt; do not overwrite it');
  }
  return dest;
}

function setup(root, tools) {
  const dest = safePath(root, path.join('.agents', 'skills', 'playwright-cli'));
  const receiptPath = safePath(root, path.join('.local', 'playwright-skill-receipt.json'));
  if (fs.existsSync(dest) || fs.existsSync(receiptPath)) throw new Error('Skill or receipt already exists; inspect it and use a fresh workspace for upgrades');
  fs.mkdirSync(path.join(root, '.local'), { recursive: true });
  const stage = fs.mkdtempSync(path.join(root, '.local', 'playwright-skill-stage-'));
  try {
    const result = spawnSync(process.execPath, [tools.bin, 'install', '--skills=agents'], {
      cwd: stage, env: { ...process.env, NO_UPDATE_NOTIFIER: '1', PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD: '1' },
      encoding: 'utf8', windowsHide: true,
    });
    if (result.error || result.status !== 0) throw new Error('Official skill installer failed');
    const staged = path.join(stage, '.agents', 'skills', 'playwright-cli');
    if (JSON.stringify(tree(staged)) !== JSON.stringify(tools.files)) throw new Error('Installed skill differs from pinned package');
    safePath(root, path.join('.agents', 'skills', 'playwright-cli'));
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    if (fs.existsSync(dest)) throw new Error('Skill appeared during setup; refusing overwrite');
    fs.renameSync(staged, dest);
    const receipt = { schemaVersion: 1, installedAt: new Date().toISOString(), versions: tools.versions,
      toolchainHashes: tools.hashes, skillFiles: tools.files };
    fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n', { flag: 'wx', mode: 0o600 });
    return check(root, tools);
  } finally {
    fs.rmSync(stage, { recursive: true, force: true });
  }
}

function main(args) {
  const command = args.shift();
  let dir = process.cwd();
  let confirm = false;
  while (args.length) {
    const arg = args.shift();
    if (arg === '--workspace' && args.length) dir = args.shift();
    else if (arg === '--confirm-install-skills') confirm = true;
    else throw new Error('Usage: playwright-skill.cjs check|setup [--workspace PATH] [--confirm-install-skills]');
  }
  if (!['check', 'setup'].includes(command) || (command === 'setup' && !confirm) || (command === 'check' && confirm)) {
    throw new Error('Use check, or setup --confirm-install-skills after dependency approval');
  }
  const root = workspace(dir);
  const tools = toolchain();
  const dest = command === 'check' ? check(root, tools) : setup(root, tools);
  console.log(`Official skill verified: ${dest}`);
  console.log(`CLI: ${tools.bin} (version ${tools.versions.cli}); @playwright/test ${tools.versions.test}; CLI Playwright/core ${tools.versions.cliCore}`);
  console.log('Private receipt: .local/playwright-skill-receipt.json');
}

if (require.main === module) {
  try { main(process.argv.slice(2)); }
  catch (error) { console.error(`Playwright skill: ${error.message}`); process.exitCode = 1; }
}

module.exports = { main, setup, check, workspace, toolchain };

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

function isWithin(parent, candidate) {
  const relative = path.relative(parent, candidate);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

function resolveNewDirectory(value) {
  let existing = path.resolve(value);
  const suffix = [];
  while (!fs.existsSync(existing)) {
    const parent = path.dirname(existing);
    if (parent === existing) throw new Error('Cannot resolve output directory');
    suffix.unshift(path.basename(existing));
    existing = parent;
  }
  return path.join(fs.realpathSync(existing), ...suffix);
}

function initialize(destination, pluginRoot = path.resolve(__dirname, '..', '..', '..')) {
  const root = fs.realpathSync(pluginRoot);
  const plugin = JSON.parse(fs.readFileSync(path.join(root, 'plugin.json'), 'utf8'));
  if (plugin.name !== 'crm-testcase' || typeof plugin.version !== 'string') throw new Error('Invalid plugin identity');
  const target = resolveNewDirectory(destination);
  if (isWithin(root, target)) throw new Error('Workspace must be outside the installed plugin directory');
  if (fs.existsSync(target)) throw new Error('Workspace already exists; choose a fresh directory');
  const kit = path.join(root, 'skills', 'crm-testcase', 'kit');
  const manifestPath = path.join(kit, 'MANIFEST.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (manifest.schemaVersion !== 1 || manifest.package !== 'CRM-Testcase-Customer-Kit' ||
      !manifest.files || typeof manifest.files !== 'object' || Array.isArray(manifest.files) ||
      Object.keys(manifest.files).length === 0) throw new Error('Invalid bundled kit manifest');
  const entries = [];
  for (const [name, digest] of Object.entries(manifest.files)) {
    if (!name || name.includes('\\') || name.startsWith('/') || /^[a-z]:/i.test(name) ||
        name.split('/').some(part => !part || part === '.' || part === '..') ||
        ['MANIFEST.json', '.crm-testcase-workspace.json'].includes(name) ||
        ['.local', 'runs', 'node_modules', '.venv'].includes(name.split('/')[0]) ||
        !/^[a-f0-9]{64}$/.test(digest)) throw new Error('Unsafe path or hash in bundled manifest');
    const source = path.join(kit, ...name.split('/'));
    if (!isWithin(kit, fs.realpathSync(source)) || !fs.lstatSync(source).isFile() || fs.lstatSync(source).isSymbolicLink()) {
      throw new Error(`Bundled file is not a regular in-bundle file: ${name}`);
    }
    const content = fs.readFileSync(source);
    if (crypto.createHash('sha256').update(content).digest('hex') !== digest) {
      throw new Error(`Bundled file differs from its manifest: ${name}`);
    }
    entries.push([name, content]);
  }
  // Verify the whole payload before creating any customer workspace.
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.mkdirSync(target);
  for (const [name, content] of entries) {
    const output = path.join(target, ...name.split('/'));
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, content, { flag: 'wx' });
  }
  fs.copyFileSync(manifestPath, path.join(target, 'MANIFEST.json'), fs.constants.COPYFILE_EXCL);
  fs.writeFileSync(path.join(target, '.crm-testcase-workspace.json'), JSON.stringify({
    schemaVersion: 1, plugin: plugin.name, pluginVersion: plugin.version,
    kitVersion: manifest.version, createdAt: new Date().toISOString(),
    note: 'Initialized code/assets only; dependencies, CRM access and approvals are not configured.',
  }, null, 2) + '\n', { flag: 'wx' });
  return { target, count: entries.length, kitVersion: manifest.version };
}

function options(args) {
  if (args.length !== 2 || args[0] !== '--workspace' || !args[1].trim() || args[1].startsWith('--')) {
    throw new Error('Usage: node initialize.cjs --workspace NEW_CUSTOMER_WORK_FOLDER');
  }
  return args[1];
}

if (require.main === module) {
  try {
    const result = initialize(options(process.argv.slice(2)));
    console.log(`Initialized ${result.target} with ${result.count} verified kit files (v${result.kitVersion}).`);
    console.log('No dependencies installed, AI calls made, CRM access performed or credentials configured. Continue with the workspace README.');
  } catch (error) {
    console.error(`Initialization failed: ${error.message}`);
    process.exitCode = 1;
  }
}

module.exports = { initialize, options, isWithin };

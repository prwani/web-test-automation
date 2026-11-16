const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const readline = require('node:readline');
const { spawn, execFile } = require('node:child_process');
const { promisify } = require('node:util');

test('Copilot natively registers all four inline-prompt plugin commands', { timeout: 90000 }, async () => {
  const plugin = path.resolve(__dirname, '..');
  const child = spawn('copilot', ['--acp', '--plugin-dir', plugin, '--disable-builtin-mcps'], {
    cwd: plugin, stdio: ['pipe', 'pipe', 'pipe'],
  });
  const exited = new Promise(resolve => child.once('close', resolve));
  child.stderr.resume();
  const lines = readline.createInterface({ input: child.stdout });
  let timeout;
  try {
    const commands = await new Promise((resolve, reject) => {
      child.once('error', reject);
      child.once('close', code => reject(new Error(`CLI closed before command discovery: ${code}`)));
      timeout = setTimeout(() => reject(new Error('Native command discovery timed out')), 60000);
      function send(id, method, params) {
        child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
      }
      lines.on('line', line => {
        let event;
        try { event = JSON.parse(line); } catch {
          reject(new Error('CLI returned invalid protocol JSON during command discovery'));
          return;
        }
        if (event.error && [1, 2].includes(event.id)) {
          reject(new Error(JSON.stringify(event.error)));
        } else if (event.id === 1) {
          send(2, 'session/new', { cwd: plugin, mcpServers: [] });
        }
        const update = event.params?.update;
        if (update?.sessionUpdate === 'available_commands_update') resolve(update.availableCommands);
      });
      send(1, 'initialize', {
        protocolVersion: 1, clientCapabilities: {},
        clientInfo: { name: 'crm-command-discovery-test', version: '1.0.0' },
      });
    });
    for (const name of ['explore', 'generate-cases', 'create-tests', 'run-tests']) {
      const command = commands.find(c => c.name === `crm-testcase:${name}`);
      assert(command, `Missing registered slash command: ${name}`);
      assert(command.description?.length > 0);
      assert(command.input, `Command must accept inline input: ${name}`);
    }
  } finally {
    clearTimeout(timeout);
    lines.close();
    child.stdin.end();
    let shutdownTimeout;
    try {
      const stopped = await Promise.race([
        exited.then(() => true),
        new Promise(resolve => { shutdownTimeout = setTimeout(() => resolve(false), 5000); }),
      ]);
      if (!stopped && child.pid) {
        if (process.platform === 'win32') {
          await promisify(execFile)('pwsh', ['-NoProfile', '-Command', `Stop-Process -Id ${child.pid}`]);
        } else {
          child.kill('SIGTERM');
        }
        await exited;
      }
    } finally {
      clearTimeout(shutdownTimeout);
    }
  }
});

import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const scriptsDir = dirname(fileURLToPath(import.meta.url));
const docsRoot = dirname(scriptsDir);
const syncScript = join(scriptsDir, 'sync-plugin-docs.mjs');
const generatedRoot = join(docsRoot, 'src', 'content', 'docs', 'servers');

test('sync generates active servers in /servers/ index and omits archived plugins', () => {
  execFileSync(process.execPath, [syncScript], { cwd: docsRoot, stdio: 'pipe' });

  const index = readFileSync(join(generatedRoot, 'index.md'), 'utf8');
  assert.match(index, /## Servers/);
  assert.doesNotMatch(index, /## Foundation/);
  assert.doesNotMatch(index, /agent-chat-plugin/);
  assert.doesNotMatch(index, /better-godot-mcp/);
  assert.doesNotMatch(index, /imagine-mcp/);

  // Retired mcp-core folder is not generated
  assert.ok(!existsSync(join(generatedRoot, 'mcp-core')));

  // Active servers exist
  for (const srv of ['wet', 'mnemo', 'crg', 'workspace', 'notion', 'email', 'telegram', 'skret']) {
    assert.ok(existsSync(join(generatedRoot, srv, 'index.md')), `missing ${srv}/index.md`);
  }
});

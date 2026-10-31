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

test('sync classifies mcp-core as foundation and active servers in /servers/ index', () => {
  execFileSync(process.execPath, [syncScript], { cwd: docsRoot, stdio: 'pipe' });

  const index = readFileSync(join(generatedRoot, 'index.md'), 'utf8');
  assert.match(index, /## Servers/);
  assert.match(index, /## Foundation[\s\S]*mcp-core/);
  assert.doesNotMatch(index, /agent-chat-plugin/);
  assert.doesNotMatch(index, /better-godot-mcp/);
  assert.doesNotMatch(index, /imagine-mcp/);

  // Active servers exist
  assert.ok(existsSync(join(generatedRoot, 'mcp-core', 'index.md')));
  assert.ok(existsSync(join(generatedRoot, 'wet', 'index.md')));
  assert.ok(existsSync(join(generatedRoot, 'mnemo', 'index.md')));
  assert.ok(existsSync(join(generatedRoot, 'crg', 'index.md')));
});

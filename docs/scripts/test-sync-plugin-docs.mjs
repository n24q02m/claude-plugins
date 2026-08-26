import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const scriptsDir = dirname(fileURLToPath(import.meta.url));
const docsRoot = dirname(scriptsDir);
const syncScript = join(scriptsDir, 'sync-plugin-docs.mjs');
const generatedRoot = join(docsRoot, 'src', 'content', 'docs', 'servers');

test('sync classifies Agent Chat as portable coordination, not an MCP server', () => {
  execFileSync(process.execPath, [syncScript], { cwd: docsRoot, stdio: 'pipe' });

  const index = readFileSync(join(generatedRoot, 'index.md'), 'utf8');
  const agentChat = readFileSync(
    join(generatedRoot, 'agent-chat-plugin', 'index.md'),
    'utf8'
  );

  assert.match(index, /## Coordination[\s\S]*agent-chat-plugin/);
  assert.doesNotMatch(index.split('## Coordination')[0], /agent-chat-plugin/);
  assert.match(agentChat, /portable CLI\/Skill/i);
  assert.match(agentChat, /not an MCP server/i);
});

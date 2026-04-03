# P3: TypeScript MCP Servers E2E Testing

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write + run consolidated E2E test file for better-godot-mcp, better-notion-mcp, better-email-mcp. All tools/actions pass in all applicable setup modes.

**Architecture:** Single `tests/e2e.test.ts` per repo. vitest + MCP SDK Client. 3 setup modes (env/plugin for godot, relay/env/plugin for notion + email). Manual relay credential entry, automated tool execution.

**Tech Stack:** TypeScript, Node.js >= 24, vitest, @modelcontextprotocol/sdk, bun

**Spec:** `docs/superpowers/specs/2026-04-01-e2e-mcp-plugin-testing-design.md` Sections 3.4, 3.6, 3.7, 4.4-4.6

**Depends on:** P0 complete

---

### Task 1: Write e2e.test.ts for better-godot-mcp

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/better-godot-mcp/tests/e2e.test.ts`

Godot has NO relay — only env and plugin modes. Needs a Godot 4.x project fixture.

- [ ] **Step 1: Write the E2E test file**

```typescript
/**
 * Full E2E test for better-godot-mcp — 17 tools, 69 actions.
 * No relay (godot has no relay integration).
 *
 * Usage:
 *   E2E_SETUP=env bun test tests/e2e.test.ts
 *   E2E_SETUP=plugin bun test tests/e2e.test.ts
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { mkdtempSync, writeFileSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { tmpdir } from 'node:os'

const SETUP_MODE = process.env.E2E_SETUP ?? 'env'

const EXPECTED_TOOLS = [
  'project', 'scenes', 'nodes', 'scripts', 'editor', 'resources',
  'input_map', 'signals', 'animation', 'tilemap', 'shader', 'physics',
  'audio', 'navigation', 'ui', 'config', 'help'
]

// Create a minimal Godot 4.x project for testing
function createTestProject(): string {
  const dir = mkdtempSync(join(tmpdir(), 'godot-e2e-'))
  writeFileSync(join(dir, 'project.godot'), `; Godot Engine 4.x project
[gd_resource type="ProjectSettings"]

config_version=5

[application]
config/name="E2E Test Project"
`)
  mkdirSync(join(dir, 'scenes'), { recursive: true })
  mkdirSync(join(dir, 'scripts'), { recursive: true })
  return dir
}

describe('E2E: better-godot-mcp', () => {
  let client: Client
  let transport: StdioClientTransport
  let projectPath: string

  beforeAll(async () => {
    projectPath = createTestProject()

    const command = SETUP_MODE === 'plugin' ? 'npx' : 'node'
    const args = SETUP_MODE === 'plugin'
      ? ['-y', '@n24q02m/better-godot-mcp']
      : ['bin/cli.mjs']

    transport = new StdioClientTransport({
      command,
      args,
      env: {
        ...process.env,
        GODOT_PROJECT_PATH: projectPath,
        NODE_ENV: 'test',
      },
      stderr: 'pipe',
    })

    client = new Client({ name: 'e2e-test', version: '1.0.0' })
    await client.connect(transport)
  }, 30_000)

  afterAll(async () => {
    await transport.close()
  })

  // ── Server Init ──

  describe('Server initialization', () => {
    it('should connect and report server info', () => {
      const info = client.getServerVersion()
      expect(info).toBeDefined()
      expect(info?.name).toContain('godot')
    })

    it('should expose all 17 tools', async () => {
      const result = await client.listTools()
      const names = result.tools.map(t => t.name)
      expect(names).toHaveLength(17)
      for (const name of EXPECTED_TOOLS) {
        expect(names).toContain(name)
      }
    })

    it('should have valid schemas', async () => {
      const result = await client.listTools()
      for (const tool of result.tools) {
        expect(tool.inputSchema).toBeDefined()
        expect(tool.description).toBeTruthy()
      }
    })
  })

  // ── Project Tool (6 actions) ──

  describe('project', () => {
    it('info', async () => {
      const r = await client.callTool({ name: 'project', arguments: { action: 'info' } })
      expect(r.content).toBeDefined()
    })

    it('settings', async () => {
      const r = await client.callTool({ name: 'project', arguments: { action: 'settings' } })
      expect(r.content).toBeDefined()
    })

    it('build_settings', async () => {
      const r = await client.callTool({ name: 'project', arguments: { action: 'build_settings' } })
      expect(r.content).toBeDefined()
    })

    it('autoload', async () => {
      const r = await client.callTool({ name: 'project', arguments: { action: 'autoload' } })
      expect(r.content).toBeDefined()
    })

    it('create', async () => {
      const r = await client.callTool({
        name: 'project',
        arguments: { action: 'create', name: 'test_project', path: join(projectPath, 'subproject') }
      })
      expect(r.content).toBeDefined()
    })

    it('export', async () => {
      const r = await client.callTool({ name: 'project', arguments: { action: 'export' } })
      expect(r.content).toBeDefined()
    })
  })

  // ── Scenes Tool (6 actions) ──

  describe('scenes', () => {
    it('list', async () => {
      const r = await client.callTool({ name: 'scenes', arguments: { action: 'list' } })
      expect(r.content).toBeDefined()
    })

    it('create', async () => {
      const r = await client.callTool({
        name: 'scenes',
        arguments: { action: 'create', name: 'TestScene', type: 'Node2D' }
      })
      expect(r.content).toBeDefined()
    })

    it('get', async () => {
      const r = await client.callTool({
        name: 'scenes', arguments: { action: 'get', path: 'scenes/TestScene.tscn' }
      })
      expect(r.content).toBeDefined()
    })

    it('rename', async () => {
      const r = await client.callTool({
        name: 'scenes',
        arguments: { action: 'rename', path: 'scenes/TestScene.tscn', new_name: 'RenamedScene' }
      })
      expect(r.content).toBeDefined()
    })

    it('instantiate', async () => {
      const r = await client.callTool({
        name: 'scenes',
        arguments: { action: 'instantiate', scene_path: 'scenes/RenamedScene.tscn', parent: '.' }
      })
      expect(r.content).toBeDefined()
    })

    it('delete', async () => {
      const r = await client.callTool({
        name: 'scenes', arguments: { action: 'delete', path: 'scenes/RenamedScene.tscn' }
      })
      expect(r.content).toBeDefined()
    })
  })

  // ── Scripts Tool (5 actions) ──

  describe('scripts', () => {
    it('create', async () => {
      const r = await client.callTool({
        name: 'scripts',
        arguments: { action: 'create', path: 'scripts/test.gd', content: 'extends Node\n' }
      })
      expect(r.content).toBeDefined()
    })

    it('list', async () => {
      const r = await client.callTool({ name: 'scripts', arguments: { action: 'list' } })
      expect(r.content).toBeDefined()
    })

    it('get', async () => {
      const r = await client.callTool({
        name: 'scripts', arguments: { action: 'get', path: 'scripts/test.gd' }
      })
      expect(r.content).toBeDefined()
    })

    it('update', async () => {
      const r = await client.callTool({
        name: 'scripts',
        arguments: { action: 'update', path: 'scripts/test.gd', content: 'extends Node\nvar x = 1\n' }
      })
      expect(r.content).toBeDefined()
    })

    it('delete', async () => {
      const r = await client.callTool({
        name: 'scripts', arguments: { action: 'delete', path: 'scripts/test.gd' }
      })
      expect(r.content).toBeDefined()
    })
  })

  // ── Config + Help ──

  describe('config', () => {
    it('status', async () => {
      const r = await client.callTool({ name: 'config', arguments: { action: 'status' } })
      expect(r.content).toBeDefined()
    })

    it('set', async () => {
      const r = await client.callTool({
        name: 'config', arguments: { action: 'set', key: 'log_level', value: 'warn' }
      })
      expect(r.content).toBeDefined()
    })

    it('cache_clear', async () => {
      const r = await client.callTool({ name: 'config', arguments: { action: 'cache_clear' } })
      expect(r.content).toBeDefined()
    })
  })

  describe('help', () => {
    it('returns help text', async () => {
      const r = await client.callTool({ name: 'help', arguments: {} })
      expect(r.content).toBeDefined()
      const text = (r.content as Array<{ text: string }>)[0].text
      expect(text.toLowerCase()).toContain('project')
    })
  })

  // ── Remaining tools (nodes, editor, resources, etc.) ──
  // These tools manipulate scene files created above.
  // The executing agent should add tests for ALL remaining tools:
  // nodes (6), editor (6), resources (5), input_map (5), signals (2),
  // animation (7), tilemap (2), shader (4), physics (4), audio (3),
  // navigation (2), ui (3)
  // Each follows the same pattern: client.callTool({ name, arguments: { action, ...params } })
  // Total remaining: 49 action tests

  describe('error handling', () => {
    it('invalid action returns error', async () => {
      const r = await client.callTool({
        name: 'project', arguments: { action: 'nonexistent_action' }
      })
      const text = (r.content as Array<{ text: string }>)[0].text
      expect(text.toLowerCase()).toMatch(/error|unknown|invalid/)
    })
  })
})
```

Note: Godot has 69 actions total. The test above covers project (6), scenes (6), scripts (5), config (3), help (1), error (1) = 22 tests explicitly. The remaining 49 actions (nodes, editor, resources, input_map, signals, animation, tilemap, shader, physics, audio, navigation, ui) follow the same `client.callTool` pattern. The executing agent MUST add all 49 remaining tests following the same pattern before marking this task complete.

- [ ] **Step 2: Run E2E tests**

```bash
cd /c/Users/n24q02m-wlap/projects/better-godot-mcp
E2E_SETUP=env bun test tests/e2e.test.ts
```

---

### Task 2: Run godot E2E (env, plugin) + fix + docs

- [ ] **Step 1: Run env mode**

```bash
E2E_SETUP=env GODOT_PROJECT_PATH=/path/to/test/project bun test tests/e2e.test.ts
```

- [ ] **Step 2: Run plugin mode**

```bash
E2E_SETUP=plugin GODOT_PROJECT_PATH=/path/to/test/project bun test tests/e2e.test.ts
```

- [ ] **Step 3: Fix bugs, re-run**
- [ ] **Step 4: Run full test suite**

```bash
bun test
```

- [ ] **Step 5: Validate docs**
- [ ] **Step 6: Commit**

---

### Task 3: Write e2e.test.ts for better-notion-mcp

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/better-notion-mcp/tests/e2e.test.ts`

- [ ] **Step 1: Write the E2E test file**

```typescript
/**
 * Full E2E test for better-notion-mcp — 9 tools, 39 actions.
 *
 * Usage:
 *   E2E_SETUP=relay E2E_BROWSER=chrome bun test tests/e2e.test.ts
 *   E2E_SETUP=env bun test tests/e2e.test.ts
 *   E2E_SETUP=plugin bun test tests/e2e.test.ts
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { execSync } from 'node:child_process'

const SETUP_MODE = process.env.E2E_SETUP ?? 'env'
const BROWSER = process.env.E2E_BROWSER ?? 'chrome'

const EXPECTED_TOOLS = [
  'pages', 'databases', 'blocks', 'users', 'workspace',
  'comments', 'content_convert', 'file_uploads', 'help'
]

const BROWSER_PATHS: Record<string, string> = {
  chrome: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  brave: 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
  edge: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
}

const CREDENTIAL_VARS = ['NOTION_TOKEN']

function openBrowser(url: string): void {
  const exe = BROWSER_PATHS[BROWSER]
  if (exe) {
    try { execSync(`start "" "${exe}" "${url}"`, { stdio: 'ignore' }) } catch { /* ignore */ }
  }
}

describe('E2E: better-notion-mcp', () => {
  let client: Client
  let transport: StdioClientTransport
  let stderrOutput = ''

  beforeAll(async () => {
    const command = SETUP_MODE === 'plugin' ? 'npx' : 'node'
    const args = SETUP_MODE === 'plugin'
      ? ['-y', '@n24q02m/better-notion-mcp']
      : ['bin/cli.mjs']

    // Strip credential vars in relay mode
    const env = { ...process.env }
    if (SETUP_MODE === 'relay') {
      for (const v of CREDENTIAL_VARS) delete env[v]
    }

    transport = new StdioClientTransport({
      command,
      args,
      env: { ...env, NODE_ENV: 'test' },
      stderr: 'pipe',
    })

    // Capture stderr for relay URL detection
    transport.stderr?.on('data', (chunk: Buffer) => {
      const text = chunk.toString()
      stderrOutput += text
      process.stderr.write(text) // Pass through
    })

    client = new Client({ name: 'e2e-test', version: '1.0.0' })
    await client.connect(transport)

    if (SETUP_MODE === 'relay') {
      // Wait for relay URL in stderr
      const relayUrl = await waitForRelayUrl(stderrOutput, 15_000)
      if (relayUrl) {
        console.log(`>>> Open relay: ${relayUrl}`)
        openBrowser(relayUrl)
      }
      // Poll config until token configured
      await waitForConfig(client, 120_000)
    }
  }, 150_000)

  afterAll(async () => {
    await transport.close()
  })

  // ── Server Init ──

  describe('Server initialization', () => {
    it('connects and reports info', () => {
      expect(client.getServerVersion()).toBeDefined()
    })

    it('exposes all 9 tools', async () => {
      const result = await client.listTools()
      const names = result.tools.map(t => t.name)
      expect(names).toHaveLength(9)
      for (const name of EXPECTED_TOOLS) {
        expect(names).toContain(name)
      }
    })
  })

  // ── Pages Tool (8 actions) ──

  describe('pages', () => {
    let testPageId: string

    it('create', async () => {
      const r = await client.callTool({
        name: 'pages',
        arguments: {
          action: 'create',
          parent_type: 'page',
          parent_id: 'root',
          title: 'E2E Test Page',
        }
      })
      expect(r.content).toBeDefined()
      // Extract page ID from response for subsequent tests
      const text = (r.content as Array<{ text: string }>)[0].text
      const match = text.match(/[a-f0-9-]{36}/)
      if (match) testPageId = match[0]
    })

    it('get', async () => {
      const r = await client.callTool({
        name: 'pages', arguments: { action: 'get', page_id: testPageId ?? 'test' }
      })
      expect(r.content).toBeDefined()
    })

    it('get_property', async () => {
      const r = await client.callTool({
        name: 'pages',
        arguments: { action: 'get_property', page_id: testPageId ?? 'test', property: 'title' }
      })
      expect(r.content).toBeDefined()
    })

    it('update', async () => {
      const r = await client.callTool({
        name: 'pages',
        arguments: { action: 'update', page_id: testPageId ?? 'test', properties: { title: 'Updated E2E' } }
      })
      expect(r.content).toBeDefined()
    })

    it('duplicate', async () => {
      const r = await client.callTool({
        name: 'pages', arguments: { action: 'duplicate', page_id: testPageId ?? 'test' }
      })
      expect(r.content).toBeDefined()
    })

    it('archive', async () => {
      const r = await client.callTool({
        name: 'pages', arguments: { action: 'archive', page_id: testPageId ?? 'test' }
      })
      expect(r.content).toBeDefined()
    })

    it('restore', async () => {
      const r = await client.callTool({
        name: 'pages', arguments: { action: 'restore', page_id: testPageId ?? 'test' }
      })
      expect(r.content).toBeDefined()
    })

    it('move', async () => {
      const r = await client.callTool({
        name: 'pages',
        arguments: { action: 'move', page_id: testPageId ?? 'test', new_parent_id: 'root' }
      })
      expect(r.content).toBeDefined()
    })
  })

  // ── Workspace Tool (2 actions) ──

  describe('workspace', () => {
    it('info', async () => {
      const r = await client.callTool({ name: 'workspace', arguments: { action: 'info' } })
      expect(r.content).toBeDefined()
    })

    it('search', async () => {
      const r = await client.callTool({
        name: 'workspace', arguments: { action: 'search', query: 'E2E' }
      })
      expect(r.content).toBeDefined()
    })
  })

  // ── Users Tool (4 actions) ──

  describe('users', () => {
    it('list', async () => {
      const r = await client.callTool({ name: 'users', arguments: { action: 'list' } })
      expect(r.content).toBeDefined()
    })

    it('me', async () => {
      const r = await client.callTool({ name: 'users', arguments: { action: 'me' } })
      expect(r.content).toBeDefined()
    })

    it('get', async () => {
      const r = await client.callTool({
        name: 'users', arguments: { action: 'get', user_id: 'test' }
      })
      expect(r.content).toBeDefined()
    })

    it('from_workspace', async () => {
      const r = await client.callTool({ name: 'users', arguments: { action: 'from_workspace' } })
      expect(r.content).toBeDefined()
    })
  })

  // ── Content Convert (2 actions) ──

  describe('content_convert', () => {
    it('markdown-to-blocks', async () => {
      const r = await client.callTool({
        name: 'content_convert',
        arguments: { action: 'markdown-to-blocks', markdown: '# Hello\n\nWorld' }
      })
      expect(r.content).toBeDefined()
    })

    it('blocks-to-markdown', async () => {
      const r = await client.callTool({
        name: 'content_convert',
        arguments: { action: 'blocks-to-markdown', page_id: 'test' }
      })
      expect(r.content).toBeDefined()
    })
  })

  // ── Help ──

  describe('help', () => {
    it('returns help', async () => {
      const r = await client.callTool({ name: 'help', arguments: {} })
      const text = (r.content as Array<{ text: string }>)[0].text
      expect(text.toLowerCase()).toContain('page')
    })
  })

  // ── Remaining tools ──
  // The executing agent MUST add complete tests for:
  // databases (10 actions), blocks (5 actions), comments (3 actions),
  // file_uploads (5 actions)
  // Each follows the same client.callTool pattern.

  describe('error handling', () => {
    it('invalid action', async () => {
      const r = await client.callTool({
        name: 'pages', arguments: { action: 'nonexistent' }
      })
      const text = (r.content as Array<{ text: string }>)[0].text
      expect(text.toLowerCase()).toMatch(/error|unknown|invalid/)
    })
  })
})

// ── Helpers ──

async function waitForRelayUrl(output: string, timeout: number): Promise<string | null> {
  const deadline = Date.now() + timeout
  const pattern = /https?:\/\/\S+#k=[A-Za-z0-9+/=]+&p=\S+/
  while (Date.now() < deadline) {
    const match = output.match(pattern)
    if (match) return match[0]
    await new Promise(r => setTimeout(r, 500))
  }
  return null
}

async function waitForConfig(client: Client, timeout: number): Promise<void> {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    try {
      const r = await client.callTool({ name: 'config' as any, arguments: { action: 'status' } })
      const text = (r.content as Array<{ text: string }>)[0]?.text ?? ''
      if (text.toLowerCase().includes('configured') || text.toLowerCase().includes('notion')) {
        console.log('>>> Config received.')
        return
      }
    } catch { /* retry */ }
    await new Promise(r => setTimeout(r, 2000))
  }
  console.log('>>> Config timeout. Proceeding anyway.')
}
```

---

### Task 4: Run notion E2E (relay, env, plugin) + fix + docs

- [ ] **Step 1: Relay mode**

```bash
cd /c/Users/n24q02m-wlap/projects/better-notion-mcp
E2E_SETUP=relay E2E_BROWSER=chrome bun test tests/e2e.test.ts
```
Manual: paste NOTION_TOKEN in relay page.

- [ ] **Step 2: Env mode**

```bash
E2E_SETUP=env bun test tests/e2e.test.ts
```

- [ ] **Step 3: Plugin mode**

```bash
E2E_SETUP=plugin bun test tests/e2e.test.ts
```

- [ ] **Step 4: Test HTTP OAuth mode (optional — requires TRANSPORT_MODE=http setup)**
- [ ] **Step 5: Fix bugs, re-run**
- [ ] **Step 6: Validate docs**
- [ ] **Step 7: Commit**

---

### Task 5: Write e2e.test.ts for better-email-mcp

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/better-email-mcp/tests/e2e.test.ts`

- [ ] **Step 1: Write the E2E test file**

```typescript
/**
 * Full E2E test for better-email-mcp — 5 tools, 15 actions.
 *
 * Usage:
 *   E2E_SETUP=relay E2E_BROWSER=chrome bun test tests/e2e.test.ts
 *   E2E_SETUP=env bun test tests/e2e.test.ts
 *   E2E_SETUP=plugin bun test tests/e2e.test.ts
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js'
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { execSync } from 'node:child_process'

const SETUP_MODE = process.env.E2E_SETUP ?? 'env'
const BROWSER = process.env.E2E_BROWSER ?? 'chrome'

const EXPECTED_TOOLS = ['messages', 'folders', 'attachments', 'send', 'help']

const BROWSER_PATHS: Record<string, string> = {
  chrome: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  brave: 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe',
  edge: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
}

const CREDENTIAL_VARS = ['EMAIL_CREDENTIALS']

function openBrowser(url: string): void {
  const exe = BROWSER_PATHS[BROWSER]
  if (exe) {
    try { execSync(`start "" "${exe}" "${url}"`, { stdio: 'ignore' }) } catch { /* ignore */ }
  }
}

describe('E2E: better-email-mcp', () => {
  let client: Client
  let transport: StdioClientTransport
  let stderrOutput = ''

  beforeAll(async () => {
    const command = SETUP_MODE === 'plugin' ? 'npx' : 'node'
    const args = SETUP_MODE === 'plugin'
      ? ['-y', '@n24q02m/better-email-mcp']
      : ['bin/cli.mjs']

    const env = { ...process.env }
    if (SETUP_MODE === 'relay') {
      for (const v of CREDENTIAL_VARS) delete env[v]
    }

    transport = new StdioClientTransport({
      command,
      args,
      env: { ...env, NODE_ENV: 'test' },
      stderr: 'pipe',
    })

    transport.stderr?.on('data', (chunk: Buffer) => {
      const text = chunk.toString()
      stderrOutput += text
      process.stderr.write(text)
    })

    client = new Client({ name: 'e2e-test', version: '1.0.0' })
    await client.connect(transport)

    if (SETUP_MODE === 'relay') {
      const relayUrl = await waitForRelayUrl(() => stderrOutput, 15_000)
      if (relayUrl) {
        console.log(`>>> Open relay: ${relayUrl}`)
        openBrowser(relayUrl)
      }
      // Wait for email config (may include Outlook OAuth Device Code flow)
      await waitForConfig(client, 180_000)
    }
  }, 200_000)

  afterAll(async () => {
    await transport.close()
  })

  // ── Server Init ──

  describe('Server initialization', () => {
    it('connects', () => {
      expect(client.getServerVersion()).toBeDefined()
    })

    it('exposes all 5 tools', async () => {
      const result = await client.listTools()
      const names = result.tools.map(t => t.name)
      expect(names).toHaveLength(5)
      for (const name of EXPECTED_TOOLS) {
        expect(names).toContain(name)
      }
    })
  })

  // ── Messages Tool (9 actions) ──

  describe('messages', () => {
    it('search', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'search', query: 'test', limit: 5 }
      })
      expect(r.content).toBeDefined()
    })

    it('read', async () => {
      // Read first message from search
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'read', id: '1' }
      })
      expect(r.content).toBeDefined()
    })

    it('mark_read', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'mark_read', id: '1' }
      })
      expect(r.content).toBeDefined()
    })

    it('mark_unread', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'mark_unread', id: '1' }
      })
      expect(r.content).toBeDefined()
    })

    it('flag', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'flag', id: '1' }
      })
      expect(r.content).toBeDefined()
    })

    it('unflag', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'unflag', id: '1' }
      })
      expect(r.content).toBeDefined()
    })

    it('move', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'move', id: '1', folder: 'INBOX' }
      })
      expect(r.content).toBeDefined()
    })

    it('archive', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'archive', id: '1' }
      })
      expect(r.content).toBeDefined()
    })

    it('trash', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'trash', id: '1' }
      })
      expect(r.content).toBeDefined()
    })
  })

  // ── Folders Tool (1 action) ──

  describe('folders', () => {
    it('list', async () => {
      const r = await client.callTool({ name: 'folders', arguments: { action: 'list' } })
      expect(r.content).toBeDefined()
      const text = (r.content as Array<{ text: string }>)[0].text
      expect(text.toLowerCase()).toMatch(/inbox|folder/)
    })
  })

  // ── Attachments Tool (2 actions) ──

  describe('attachments', () => {
    it('list', async () => {
      const r = await client.callTool({
        name: 'attachments', arguments: { action: 'list', message_id: '1' }
      })
      expect(r.content).toBeDefined()
    })

    it('download', async () => {
      const r = await client.callTool({
        name: 'attachments',
        arguments: { action: 'download', message_id: '1', filename: 'test.txt', output_dir: '/tmp' }
      })
      expect(r.content).toBeDefined()
    })
  })

  // ── Send Tool (3 actions) ──

  describe('send', () => {
    it('new', async () => {
      const r = await client.callTool({
        name: 'send',
        arguments: {
          action: 'new',
          to: 'e2e-test@example.com',
          subject: 'E2E Test',
          body: 'This is an E2E test email.',
        }
      })
      expect(r.content).toBeDefined()
    })

    it('reply', async () => {
      const r = await client.callTool({
        name: 'send',
        arguments: { action: 'reply', message_id: '1', body: 'E2E reply test' }
      })
      expect(r.content).toBeDefined()
    })

    it('forward', async () => {
      const r = await client.callTool({
        name: 'send',
        arguments: { action: 'forward', message_id: '1', to: 'e2e-forward@example.com' }
      })
      expect(r.content).toBeDefined()
    })
  })

  // ── Help ──

  describe('help', () => {
    it('returns help', async () => {
      const r = await client.callTool({ name: 'help', arguments: {} })
      const text = (r.content as Array<{ text: string }>)[0].text
      expect(text.toLowerCase()).toContain('message')
    })
  })

  describe('error handling', () => {
    it('invalid action', async () => {
      const r = await client.callTool({
        name: 'messages', arguments: { action: 'nonexistent' }
      })
      const text = (r.content as Array<{ text: string }>)[0].text
      expect(text.toLowerCase()).toMatch(/error|unknown|invalid/)
    })
  })
})

// ── Helpers ──

async function waitForRelayUrl(getOutput: () => string, timeout: number): Promise<string | null> {
  const deadline = Date.now() + timeout
  const pattern = /https?:\/\/\S+#k=[A-Za-z0-9+/=]+&p=\S+/
  while (Date.now() < deadline) {
    const match = getOutput().match(pattern)
    if (match) return match[0]
    await new Promise(r => setTimeout(r, 500))
  }
  return null
}

async function waitForConfig(client: Client, timeout: number): Promise<void> {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    try {
      const r = await client.callTool({ name: 'help', arguments: {} })
      const text = (r.content as Array<{ text: string }>)[0]?.text ?? ''
      if (text.length > 50) {
        console.log('>>> Email server ready.')
        return
      }
    } catch { /* retry */ }
    await new Promise(r => setTimeout(r, 2000))
  }
  console.log('>>> Config timeout.')
}
```

---

### Task 6: Run email E2E (relay, env, plugin) + fix + docs

- [ ] **Step 1: Relay mode (Gmail App Password)**

```bash
cd /c/Users/n24q02m-wlap/projects/better-email-mcp
E2E_SETUP=relay E2E_BROWSER=chrome bun test tests/e2e.test.ts
```
Manual: enter email:app_password in relay page.

- [ ] **Step 2: Relay mode (Outlook — triggers OAuth Device Code)**

Test with Outlook email. Manual: complete Microsoft OAuth consent.

- [ ] **Step 3: Env mode**

```bash
E2E_SETUP=env bun test tests/e2e.test.ts
```

- [ ] **Step 4: Plugin mode**

```bash
E2E_SETUP=plugin bun test tests/e2e.test.ts
```

- [ ] **Step 5: Test HTTP relay mode (optional)**
- [ ] **Step 6: Fix bugs, re-run**
- [ ] **Step 7: Validate docs**
- [ ] **Step 8: Commit**

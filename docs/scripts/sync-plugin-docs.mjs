#!/usr/bin/env node
/**
 * Sync per-plugin markdown files from ../plugins/<name>/*.md
 * into ./src/content/docs/servers/<name>/*.md before astro build.
 *
 * Adds frontmatter editUrl pointing to source file in plugins/<name>/
 * (so Starlight "Edit this page" links jump to canonical source, not
 * the generated copy).
 *
 * Also synthesizes an `index.md` landing page per server section so the
 * bare section root `mcp.n24q02m.com/servers/<name>/` renders a real page
 * instead of 404ing (Starlight only routes directories that contain an
 * index file). The landing pulls its tagline from the plugin manifest and
 * links every sibling page in the section.
 *
 * Run via:
 *   node docs/scripts/sync-plugin-docs.mjs
 *
 * Wired automatically via package.json prebuild + predev hooks.
 */

import { readdir, mkdir, readFile, writeFile, rm, stat } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DOCS_ROOT = dirname(__dirname); // docs/
const PLUGINS_DIR = join(DOCS_ROOT, '..', 'plugins');
const TARGET_DIR = join(DOCS_ROOT, 'src', 'content', 'docs', 'servers');

// Files we expect per plugin (some optional). Order here drives the order of
// the "In this section" links on each generated section landing page, so keep
// overview.md first.
const PLUGIN_FILES = [
  'overview.md',
  'setup.md',
  'setup-with-agent.md',
  'tools.md',
  'modes.md',
  'troubleshooting.md',
  // mcp-core specific (Foundation library, no setup flow):
  'architecture.md',
  'trust-model.md',
  'migration.md',
  'shared-services.md',
  // imagine-mcp specific:
];

const REPO_RAW_BASE = 'https://github.com/n24q02m/claude-plugins/edit/main/plugins';

// mcp-core is a foundation library, not a runnable server — frame it that way
// and skip the marketplace-install pointer (it has no end-user install flow).
const FOUNDATION = 'mcp-core';
const FOUNDATION_DESCRIPTION =
  'Foundation library for the n24q02m MCP stack — shared Streamable HTTP transport, ' +
  'OAuth 2.1 Authorization Server, lifecycle management, and credential-relay primitives ' +
  'consumed by every server. Not a runnable MCP server.';

async function pathExists(p) {
  try { await stat(p); return true; } catch { return false; }
}

// "setup-with-agent.md" -> "Setup with agent"
function titleFromFile(file) {
  const base = file.replace(/\.md$/, '').replace(/-/g, ' ');
  return base.charAt(0).toUpperCase() + base.slice(1);
}

// Read display name + tagline from the plugin manifest (best-effort).
async function readPluginMeta(pluginName) {
  const manifest = join(PLUGINS_DIR, pluginName, '.claude-plugin', 'plugin.json');
  if (await pathExists(manifest)) {
    try {
      const pj = JSON.parse(await readFile(manifest, 'utf-8'));
      return { name: pj.name || pluginName, description: pj.description || '' };
    } catch {
      // malformed manifest — fall through to defaults
    }
  }
  return { name: pluginName, description: '' };
}

// YAML-safe scalar (descriptions contain ":" and em dashes).
function yamlQuote(value) {
  return `"${value.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\s*\n\s*/g, ' ').trim()}"`;
}

// Synthesize the section landing page so /servers/<name>/ resolves.
function buildIndex(pluginName, meta, copiedFiles) {
  const isFoundation = pluginName === FOUNDATION;
  const description =
    meta.description || (isFoundation ? FOUNDATION_DESCRIPTION : `${pluginName} — part of the n24q02m MCP server stack.`);
  const repoUrl = `https://github.com/n24q02m/${pluginName}`;
  const editUrl = `${REPO_RAW_BASE}/${pluginName}/.claude-plugin/plugin.json`;

  const pageLinks = copiedFiles
    .filter((f) => f !== 'index.md')
    .map((f) => `- [${titleFromFile(f)}](./${f.replace(/\.md$/, '')}/)`)
    .join('\n');

  const lines = [
    '---',
    `title: ${yamlQuote(meta.name || pluginName)}`,
    `description: ${yamlQuote(description)}`,
    `editUrl: ${editUrl}`,
    '---',
    '',
    description,
    '',
    '## In this section',
    '',
    pageLinks,
    '',
    '## Source',
    '',
    `- [GitHub: n24q02m/${pluginName}](${repoUrl})`,
  ];
  if (!isFoundation) {
    lines.push('- Install via the [n24q02m plugin marketplace](/get-started/plugin-marketplace/)');
  }
  lines.push('');
  return lines.join('\n');
}

// Synthesize the top-level /servers/ landing so the section root resolves
// instead of 404ing, listing every server with a one-line description + link.
// `entries` is [{ name, description, isFoundation }] for plugins with content.
function buildServersIndex(entries) {
  const servers = entries.filter((e) => !e.isFoundation).sort((a, b) => a.name.localeCompare(b.name));
  const foundation = entries.filter((e) => e.isFoundation);

  const toItem = (e) => `- [${e.name}](/servers/${e.name}/) -- ${e.description}`;

  const lines = [
    '---',
    'title: Servers',
    'description: All MCP servers in the n24q02m stack, plus the mcp-core foundation library.',
    '---',
    '',
    'Every server in the stack shares one foundation library (`mcp-core`), one plugin marketplace, and one multi-user auth model. Browse the servers below, or see the [server comparison](/reference/server-comparison/) for a side-by-side table.',
    '',
    '## Servers',
    '',
    ...servers.map(toItem),
  ];
  if (foundation.length > 0) {
    lines.push('', '## Foundation', '', ...foundation.map(toItem));
  }
  lines.push(
    '',
    '## See also',
    '',
    '- [Server comparison](/reference/server-comparison/)',
    '- [Modes overview](/get-started/modes-overview/)',
    '- [Plugin marketplace](/get-started/plugin-marketplace/)',
    ''
  );
  return lines.join('\n');
}

async function syncOne(pluginName, file) {
  const src = join(PLUGINS_DIR, pluginName, file);
  if (!(await pathExists(src))) return false;

  const content = await readFile(src, 'utf-8');

  // Inject editUrl into frontmatter so "Edit this page" points to source.
  // If file already has frontmatter, append; else create one.
  const editUrl = `${REPO_RAW_BASE}/${pluginName}/${file}`;
  let updated;
  const fmMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (fmMatch) {
    const existingFm = fmMatch[1];
    const body = fmMatch[2];
    if (existingFm.includes('editUrl:')) {
      // Replace existing editUrl
      const newFm = existingFm.replace(/editUrl:.*$/m, `editUrl: ${editUrl}`);
      updated = `---\n${newFm}\n---\n${body}`;
    } else {
      updated = `---\n${existingFm}\neditUrl: ${editUrl}\n---\n${body}`;
    }
  } else {
    // No existing frontmatter — synthesize minimal one
    const title = file.replace(/\.md$/, '').replace(/-/g, ' ');
    const titleCased = title.charAt(0).toUpperCase() + title.slice(1);
    updated = `---\ntitle: ${titleCased}\neditUrl: ${editUrl}\n---\n\n${content}`;
  }

  const dest = join(TARGET_DIR, pluginName, file);
  await mkdir(dirname(dest), { recursive: true });
  await writeFile(dest, updated, 'utf-8');
  return true;
}

async function main() {
  // Clean target dir to avoid stale files when source removed
  await rm(TARGET_DIR, { recursive: true, force: true });

  if (!(await pathExists(PLUGINS_DIR))) {
    console.error(`ERROR: plugins dir not found at ${PLUGINS_DIR}`);
    process.exit(1);
  }

  const plugins = (await readdir(PLUGINS_DIR, { withFileTypes: true }))
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  if (plugins.length === 0) {
    console.error(`WARNING: no plugin folders in ${PLUGINS_DIR}`);
    return;
  }

  const pluginResults = await Promise.all(
    plugins.map(async (name) => {
      const fileResults = await Promise.all(
        PLUGIN_FILES.map(async (file) => {
          const synced = await syncOne(name, file);
          return synced ? file : null;
        })
      );

      const copiedFiles = fileResults.filter(Boolean);

      if (copiedFiles.length > 0) {
        const meta = await readPluginMeta(name);
        // Generate the section landing page unless the source already ships one.
        if (!copiedFiles.includes('index.md')) {
          await writeFile(
            join(TARGET_DIR, name, 'index.md'),
            buildIndex(name, meta, copiedFiles),
            'utf-8'
          );
        }
        console.log(`  ${name}: ${copiedFiles.length} file(s) + index`);
        const isFoundation = name === FOUNDATION;
        const description =
          meta.description ||
          (isFoundation ? FOUNDATION_DESCRIPTION : `${name} — part of the n24q02m MCP server stack.`);
        return { name, count: copiedFiles.length, description, isFoundation };
      }
      return { name, count: 0 };
    })
  );

  const entries = pluginResults.filter((r) => r.count > 0);

  // Synthesize the top-level /servers/ landing so the section root resolves.
  await mkdir(TARGET_DIR, { recursive: true });
  await writeFile(join(TARGET_DIR, 'index.md'), buildServersIndex(entries), 'utf-8');

  const pluginsWithContent = entries.length;
  const totalCopied = entries.reduce((sum, r) => sum + r.count, 0);

  console.log(`\n✓ Synced ${totalCopied} file(s) across ${pluginsWithContent} plugin(s) + /servers/ index.`);
}

main().catch((err) => {
  console.error('sync-plugin-docs failed:', err);
  process.exit(1);
});

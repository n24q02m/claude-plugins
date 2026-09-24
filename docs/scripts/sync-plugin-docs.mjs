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

// Docs slugs follow the renamed GitHub repos (wet, mnemo, crg — renamed
// 2026-09-13), while plugins/<dir> keeps the marketplace plugin id. Map
// marketplace dir -> docs slug; unlisted dirs use their own name.
const SLUG_MAP = {
  'wet-mcp': 'wet',
  'mnemo-mcp': 'mnemo',
  'better-code-review-graph': 'crg',
};

// Canonical GitHub repo per marketplace dir (renamed repos differ from the
// plugin id). Used for "GitHub: n24q02m/<repo>" links on generated pages.
const REPO_NAME = {
  'wet-mcp': 'wet',
  'mnemo-mcp': 'mnemo',
  'better-code-review-graph': 'crg',
};

// Repos archived on GitHub (2026-09-13): docs stay reachable but are marked
// archived and grouped under a collapsed sidebar section.
const ARCHIVED = new Set([
  'imagine-mcp',
  'better-telegram-mcp',
  'better-notion-mcp',
  'better-email-mcp',
  'better-godot-mcp',
  'better-workspace-mcp',
]);
const ARCHIVED_BANNER =
  ':::caution[Archived]\n' +
  'This project is archived and no longer maintained. The documentation below is kept for reference.\n' +
  ':::';

function slugFor(pluginName) {
  return SLUG_MAP[pluginName] || pluginName;
}

function repoFor(pluginName) {
  return REPO_NAME[pluginName] || pluginName;
}

// Rewrite /servers/<plugin-id>/ links to the docs slug for every renamed
// server — not just the file's own plugin — so cross-links keep working.
function rewriteServerLinks(content) {
  for (const [id, slug] of Object.entries(SLUG_MAP)) {
    content = content.replace(new RegExp(`/servers/${id}/`, 'g'), `/servers/${slug}/`);
  }
  return content;
}

// Display name for generated pages: renamed servers use the new repo name,
// everything else uses the manifest/plugin id.
function displayName(pluginName, meta) {
  if (SLUG_MAP[pluginName]) return SLUG_MAP[pluginName];
  return meta.name || pluginName;
}

// mcp-core is a foundation library, not a runnable server — frame it that way
// and skip the marketplace-install pointer (it has no end-user install flow).
const FOUNDATION = 'mcp-core';
const FOUNDATION_DESCRIPTION =
  'Foundation library for the n24q02m MCP stack — shared Streamable HTTP transport, ' +
  'OAuth 2.1 Authorization Server, lifecycle management, and credential-relay primitives ' +
  'consumed by every server. Not a runnable MCP server.';
const COORDINATION = 'agent-chat-plugin';
const COORDINATION_DESCRIPTION =
  'Portable CLI/Skill coordination for peer agent sessions using shared Markdown and JSON files. ' +
  'Not an MCP server and not an agent executor.';

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

// Synthesize the section landing page so /servers/<slug>/ resolves.
function buildIndex(pluginName, meta, copiedFiles) {
  const slug = slugFor(pluginName);
  const isFoundation = pluginName === FOUNDATION;
  const isCoordination = pluginName === COORDINATION;
  const isArchived = ARCHIVED.has(pluginName);
  const description =
    meta.description ||
    (isFoundation
      ? FOUNDATION_DESCRIPTION
      : isCoordination
        ? COORDINATION_DESCRIPTION
        : `${slug} — part of the n24q02m MCP server stack.`);
  const repoUrl = `https://github.com/n24q02m/${repoFor(pluginName)}`;
  const editUrl = `${REPO_RAW_BASE}/${pluginName}/.claude-plugin/plugin.json`;

  const pageLinks = copiedFiles
    .filter((f) => f !== 'index.md')
    .map((f) => `- [${titleFromFile(f)}](./${f.replace(/\.md$/, '')}/)`)
    .join('\n');

  const lines = [
    '---',
    `title: ${yamlQuote(isArchived ? `${displayName(pluginName, meta)} (archived)` : displayName(pluginName, meta))}`,
    `description: ${yamlQuote(description)}`,
    `editUrl: ${editUrl}`,
    '---',
    '',
    ...(isArchived ? [ARCHIVED_BANNER, ''] : []),
    description,
    ...(isCoordination
      ? ['This is a portable CLI/Skill coordination plugin, not an MCP server.']
      : []),
    '',
    '## In this section',
    '',
    pageLinks,
    '',
    '## Source',
    '',
    `- [GitHub: n24q02m/${repoFor(pluginName)}](${repoUrl})`,
  ];
  if (!isFoundation) {
    lines.push('- Install via the [n24q02m plugin marketplace](/get-started/plugin-marketplace/)');
  }
  lines.push('');
  return lines.join('\n');
}

// Synthesize the top-level /servers/ landing so the section root resolves
// instead of 404ing. The route retains its historical name, while coordination
// plugins are classified separately from runnable MCP servers.
// `entries` is [{ name, slug, description, isFoundation, isCoordination, isArchived }].
function buildServersIndex(entries) {
  const servers = entries
    .filter((entry) => !entry.isFoundation && !entry.isCoordination && !entry.isArchived)
    .sort((a, b) => a.slug.localeCompare(b.slug));
  const archived = entries
    .filter((entry) => entry.isArchived)
    .sort((a, b) => a.slug.localeCompare(b.slug));
  const coordination = entries.filter((entry) => entry.isCoordination);
  const foundation = entries.filter((entry) => entry.isFoundation);

  const toItem = (e) => `- [${e.slug}](/servers/${e.slug}/) -- ${e.description}`;

  const lines = [
    '---',
    'title: Servers and coordination',
    'description: MCP servers, portable coordination plugins, and the mcp-core foundation library.',
    '---',
    '',
    'The stack shares one foundation library (`mcp-core`) and one plugin marketplace. Runnable MCP servers and portable coordination plugins remain distinct capabilities.',
    '',
    '## Servers',
    '',
    ...servers.map(toItem),
  ];
  if (archived.length > 0) {
    lines.push('', '## Archived', '', ...archived.map(toItem));
  }
  if (coordination.length > 0) {
    lines.push('', '## Coordination', '', ...coordination.map(toItem));
  }
  if (foundation.length > 0) {
    lines.push('', '## Foundation', '', ...foundation.map(toItem));
  }
  lines.push(
    '',
    '## See also',
    '',
    '- [Server comparison](/reference/server-comparison/)',
    '- [Fastretrieval library](/reference/fastretrieval/)',
    '- [Modes overview](/get-started/modes-overview/)',
    '- [Plugin marketplace](/get-started/plugin-marketplace/)',
    ''
  );
  return lines.join('\n');
}

async function syncOne(pluginName, file) {
  const src = join(PLUGINS_DIR, pluginName, file);
  if (!(await pathExists(src))) return false;

  const content = rewriteServerLinks(await readFile(src, 'utf-8'));

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

  // Archived plugins get the banner on every synced page, not just the
  // generated landing — a deep link must not look maintained.
  if (ARCHIVED.has(pluginName)) {
    updated = updated.replace(/^(---\r?\n[\s\S]*?\r?\n---\r?\n)/, `$1\n${ARCHIVED_BANNER}\n`);
  }

  const dest = join(TARGET_DIR, slugFor(pluginName), file);
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
        const slug = slugFor(name);
        const isArchived = ARCHIVED.has(name);
        // Generate the section landing page unless the source already ships one.
        if (!copiedFiles.includes('index.md')) {
          await writeFile(
            join(TARGET_DIR, slug, 'index.md'),
            buildIndex(name, meta, copiedFiles),
            'utf-8'
          );
        }
        console.log(`  ${name} -> /servers/${slug}/: ${copiedFiles.length} file(s) + index`);
        const isFoundation = name === FOUNDATION;
        const isCoordination = name === COORDINATION;
        const description =
          meta.description ||
          (isFoundation
            ? FOUNDATION_DESCRIPTION
            : isCoordination
              ? COORDINATION_DESCRIPTION
              : `${name} — part of the n24q02m MCP server stack.`);
        return {
          name,
          slug,
          count: copiedFiles.length,
          description,
          isFoundation,
          isCoordination,
          isArchived,
        };
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

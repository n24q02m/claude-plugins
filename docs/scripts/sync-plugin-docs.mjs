#!/usr/bin/env node
/**
 * Sync per-plugin markdown files from ../plugins/<name>/*.md
 * into ./src/content/docs/servers/<name>/*.md before astro build.
 *
 * Adds frontmatter editUrl pointing to source file in plugins/<name>/
 * (so Starlight "Edit this page" links jump to canonical source, not
 * the generated copy).
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

// Files we expect per plugin (some optional)
const PLUGIN_FILES = [
  'setup.md',
  'setup-with-agent.md',
  'tools.md',
  'modes.md',
  'troubleshooting.md',
  'overview.md',
  // mcp-core specific (Foundation library, no setup flow):
  'architecture.md',
  'trust-model.md',
  'migration.md',
  'shared-services.md',
  // imagine-mcp specific:
  'models.md',
];

const REPO_RAW_BASE = 'https://github.com/n24q02m/claude-plugins/edit/main/plugins';

async function pathExists(p) {
  try { await stat(p); return true; } catch { return false; }
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

  let totalCopied = 0;
  let pluginsWithContent = 0;
  for (const name of plugins) {
    let copiedForPlugin = 0;
    for (const file of PLUGIN_FILES) {
      if (await syncOne(name, file)) {
        copiedForPlugin += 1;
      }
    }
    if (copiedForPlugin > 0) {
      pluginsWithContent += 1;
      console.log(`  ${name}: ${copiedForPlugin} file(s)`);
    }
    totalCopied += copiedForPlugin;
  }

  console.log(`\n✓ Synced ${totalCopied} file(s) across ${pluginsWithContent} plugin(s).`);
}

main().catch((err) => {
  console.error('sync-plugin-docs failed:', err);
  process.exit(1);
});

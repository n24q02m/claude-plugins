#!/usr/bin/env node
/**
 * Sync the tools-docs site content (skret / better-semantic-release /
 * better-drive) into ./src/content/docs/tools/ before astro build, so
 * mcp.n24q02m.com serves the tools docs under /tools/ (G1 consolidation,
 * 2026-09-17).
 *
 * Source resolution order:
 *   1. TOOLS_DOCS_DIR env var (CI sets it to the checked-out tools-docs repo)
 *   2. sibling checkout ../tools-docs (local dev)
 *   3. absent -> a stub index.md is written so local builds stay green;
 *      CI always provides the checkout, so the stub never deploys.
 *
 * Rewrites applied per page:
 *   - root-relative links (/skret/..., /bsr/..., /bdrive/...,
 *     /get-started/..., /reference/...) are prefixed with /tools/ so they
 *     resolve inside the section instead of the site root;
 *   - frontmatter gains editUrl pointing at the canonical source file in
 *     n24q02m/tools-docs (same convention as sync-plugin-docs.mjs).
 *
 * Run via:
 *   node docs/scripts/sync-tools-docs.mjs
 *
 * Wired automatically via package.json prebuild + predev hooks.
 */

import { readdir, mkdir, readFile, writeFile, rm, stat, cp } from 'node:fs/promises';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DOCS_ROOT = dirname(__dirname); // docs/
const TARGET_DIR = join(DOCS_ROOT, 'src', 'content', 'docs', 'tools');
const TOOLS_REPO = 'https://github.com/n24q02m/tools-docs/edit/main/src/content/docs';

// Root-relative prefixes that belong to the tools section after the merge.
const SECTION_PREFIXES = ['skret', 'bsr', 'bdrive', 'get-started', 'reference'];

async function pathExists(p) {
  try { await stat(p); return true; } catch { return false; }
}

function sourceDir() {
  const candidates = [
    process.env.TOOLS_DOCS_DIR,
    join(DOCS_ROOT, '..', 'tools-docs'),
  ].filter(Boolean);
  return candidates;
}

function rewriteLinks(content) {
  // Rewrite markdown links and hero/frontmatter links that start with a
  // section prefix at site root: ](/skret/x) -> ](/tools/skret/x),
  // link: /bsr/overview/ -> link: /tools/bsr/overview/.
  for (const prefix of SECTION_PREFIXES) {
    const re = new RegExp(`([(:\\s"'])/${prefix}/`, 'g');
    content = content.replace(re, `$1/tools/${prefix}/`);
  }
  return content;
}

function injectEditUrl(content, relPath) {
  const editUrl = `${TOOLS_REPO}/${relPath}`;
  const fmMatch = content.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/);
  if (fmMatch) {
    const [, fm, body] = fmMatch;
    if (fm.includes('editUrl:')) {
      return `---\n${fm.replace(/editUrl:.*$/m, `editUrl: ${editUrl}`)}\n---\n${body}`;
    }
    return `---\n${fm}\neditUrl: ${editUrl}\n---\n${body}`;
  }
  return `---\neditUrl: ${editUrl}\n---\n\n${content}`;
}

async function* walk(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const p = join(dir, entry.name);
    if (entry.isDirectory()) yield* walk(p);
    else if (/\.(md|mdx)$/.test(entry.name)) yield p;
  }
}

async function writeStub() {
  await mkdir(TARGET_DIR, { recursive: true });
  await writeFile(
    join(TARGET_DIR, 'index.md'),
    [
      '---',
      'title: Tools',
      'description: skret, better-semantic-release and better-drive documentation.',
      '---',
      '',
      'Tools documentation is synced from the `tools-docs` repository at build',
      'time. This stub only appears when the sibling `tools-docs` checkout (or',
      '`TOOLS_DOCS_DIR`) is absent — CI always provides it.',
      '',
    ].join('\n'),
    'utf-8'
  );
  console.log('  tools-docs source not found — wrote stub /tools/ index (local build only).');
}

async function main() {
  await rm(TARGET_DIR, { recursive: true, force: true });

  let src = null;
  for (const candidate of sourceDir()) {
    const contentDir = join(candidate, 'src', 'content', 'docs');
    if (await pathExists(contentDir)) {
      src = contentDir;
      break;
    }
  }

  if (!src) {
    await writeStub();
    return;
  }

  let copied = 0;
  for await (const file of walk(src)) {
    const rel = relative(src, file).replace(/\\/g, '/');
    // The tools-docs site root index becomes the /tools/ landing page.
    const destRel = rel === 'index.mdx' ? 'index.mdx' : rel;
    const raw = await readFile(file, 'utf-8');
    const out = injectEditUrl(rewriteLinks(raw), rel);
    const dest = join(TARGET_DIR, destRel);
    await mkdir(dirname(dest), { recursive: true });
    await writeFile(dest, out, 'utf-8');
    copied += 1;
  }

  console.log(`\n✓ Synced ${copied} tools-docs page(s) into /tools/.`);
}

main().catch((err) => {
  console.error('sync-tools-docs failed:', err);
  process.exit(1);
});

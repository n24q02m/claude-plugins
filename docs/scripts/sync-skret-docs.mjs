#!/usr/bin/env node
/**
 * Sync the skret docs site content into ./src/content/docs/skret/ before
 * astro build, so the unified docs hub serves skret docs under /skret/
 * (docs.n24q02m.com consolidation, 2026-09-17).
 *
 * Source resolution order:
 *   1. SKRET_DOCS_DIR env var (CI sets it to the checked-out skret repo)
 *   2. sibling checkout ../skret (local dev)
 *   3. absent -> a stub index.md is written so local builds stay green;
 *      CI always provides the checkout, so the stub never deploys.
 *
 * Rewrites applied per page:
 *   - root-relative links (/guide/..., /providers/..., /integrations/...,
 *     /migration/..., /reference/..., /contributing/..., /faq...) are
 *     prefixed with /skret/ so they resolve inside the section;
 *   - hero image `file: ../../assets/...` is rewritten to the copied
 *     /skret-assets/ public path (skret's own assets are not part of this
 *     site's src tree);
 *   - frontmatter gains editUrl pointing at the canonical source file in
 *     n24q02m/skret.
 *
 * Run via:
 *   node docs/scripts/sync-skret-docs.mjs
 *
 * Wired automatically via package.json prebuild + predev hooks.
 */

import { readdir, mkdir, readFile, writeFile, rm, stat, cp } from 'node:fs/promises';
import { join, dirname, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DOCS_ROOT = dirname(__dirname); // docs/
const TARGET_DIR = join(DOCS_ROOT, 'src', 'content', 'docs', 'skret');
const ASSETS_TARGET = join(DOCS_ROOT, 'src', 'assets', 'skret');
const SKRET_REPO = 'https://github.com/n24q02m/skret/edit/main/docs/src/content/docs';

// Root-relative prefixes that belong to the skret section after the merge.
const SECTION_PREFIXES = [
  'guide', 'providers', 'integrations', 'migration',
  'reference', 'contributing', 'faq',
];

async function pathExists(p) {
  try { await stat(p); return true; } catch { return false; }
}

function sourceDir() {
  return [
    process.env.SKRET_DOCS_DIR,
    join(DOCS_ROOT, '..', 'skret'),
  ].filter(Boolean);
}

function rewriteLinks(content) {
  for (const prefix of SECTION_PREFIXES) {
    const re = new RegExp(`([(:\\s"'])/${prefix}/`, 'g');
    content = content.replace(re, `$1/skret/${prefix}/`);
  }
  // faq.md is a root-level page: ](/faq) or link: /faq -> /skret/faq/
  content = content.replace(/([(:\s"'])\/faq(\/?)[)\s"']/g, '$1/skret/faq/$2');
  return content;
}

function rewriteAssets(content) {
  // skret docs reference ../../assets/<file> (docs/src/assets in the skret
  // repo). We copy them to src/assets/skret/ so Astro's image pipeline can
  // resolve them; from src/content/docs/skret/<page> the relative path is
  // ../../../assets/skret/<file>.
  return content.replace(
    /file:\s*\.\.\/\.\.\/assets\/(\S+)/g,
    'file: ../../../assets/skret/$1'
  );
}

function injectEditUrl(content, relPath) {
  const editUrl = `${SKRET_REPO}/${relPath}`;
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
      'title: skret',
      'description: Cloud-provider secret manager CLI documentation.',
      '---',
      '',
      'skret documentation is synced from the `skret` repository at build',
      'time. This stub only appears when the sibling `skret` checkout (or',
      '`SKRET_DOCS_DIR`) is absent — CI always provides it.',
      '',
    ].join('\n'),
    'utf-8'
  );
  console.log('  skret docs source not found — wrote stub /skret/ index (local build only).');
}

async function main() {
  await rm(TARGET_DIR, { recursive: true, force: true });
  await rm(ASSETS_TARGET, { recursive: true, force: true });

  let srcRoot = null;
  for (const candidate of sourceDir()) {
    const contentDir = join(candidate, 'docs', 'src', 'content', 'docs');
    if (await pathExists(contentDir)) {
      srcRoot = candidate;
      break;
    }
  }
  // skret repo layout: docs/src/content/docs (docs is a sub-package)
  let src = srcRoot ? join(srcRoot, 'docs', 'src', 'content', 'docs') : null;

  if (!src) {
    await writeStub();
    return;
  }

  // Copy assets (hero logo etc.) referenced as ../../assets/*.
  const assetsSrc = join(srcRoot, 'docs', 'src', 'assets');
  if (await pathExists(assetsSrc)) {
    await mkdir(ASSETS_TARGET, { recursive: true });
    await cp(assetsSrc, ASSETS_TARGET, { recursive: true });
  }

  let copied = 0;
  for await (const file of walk(src)) {
    const rel = relative(src, file).replace(/\\/g, '/');
    const raw = await readFile(file, 'utf-8');
    const out = injectEditUrl(rewriteAssets(rewriteLinks(raw)), rel);
    const dest = join(TARGET_DIR, rel);
    await mkdir(dirname(dest), { recursive: true });
    await writeFile(dest, out, 'utf-8');
    copied += 1;
  }

  console.log(`\n✓ Synced ${copied} skret docs page(s) into /skret/.`);
}

main().catch((err) => {
  console.error('sync-skret-docs failed:', err);
  process.exit(1);
});

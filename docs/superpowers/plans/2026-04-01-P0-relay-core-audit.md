# P0: Relay-Core Cross-Browser Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure mcp-relay-core relay frontend works on all browsers (not just Chromium), fix any issues, verify on Brave/Chrome/Edge.

**Architecture:** Audit 6 relay pages + shared assets (crypto.js, relay-client.js, style.css) for browser-incompatible APIs. Fix issues. Manual test on 3 browsers. Run existing test suite.

**Tech Stack:** HTML/CSS/JS (vanilla), WebCrypto API, Fetch API, Playwright (existing E2E)

**Spec:** `docs/superpowers/specs/2026-04-01-e2e-mcp-plugin-testing-design.md` Section 5

**Repo:** `C:/Users/n24q02m-wlap/projects/mcp-relay-core`

---

### Task 1: Audit shared/crypto.js for browser compatibility

**Files:**
- Read: `pages/shared/crypto.js`

- [ ] **Step 1: Grep for Chrome-only or vendor-prefixed APIs**

Run:
```bash
cd /c/Users/n24q02m-wlap/projects/mcp-relay-core
grep -n "chrome\.\|webkit\|moz\|ms[A-Z]" pages/shared/crypto.js
```
Expected: No matches. If matches found, document line numbers.

- [ ] **Step 2: Verify WebCrypto usage is standard**

Read `pages/shared/crypto.js` and verify:
- `crypto.subtle.generateKey` uses standard params (ECDH P-256)
- `crypto.subtle.deriveKey` / `deriveBits` uses HKDF-SHA256
- `crypto.subtle.encrypt` / `decrypt` uses AES-256-GCM
- `crypto.subtle.importKey` / `exportKey` uses standard formats (raw, jwk, spki)
- No `window.crypto` polyfills or browser-specific branches

- [ ] **Step 3: Check base64 handling**

Verify `atob` / `btoa` usage:
- v1.2.0 added `atob fallback` — verify the fallback handles non-ASCII correctly
- Check if `TextEncoder`/`TextDecoder` is used (standard, all browsers)
- Grep: `grep -n "atob\|btoa\|TextEncoder\|TextDecoder\|Buffer\." pages/shared/crypto.js`
- `Buffer.` is Node.js-only — MUST NOT appear in frontend code

- [ ] **Step 4: Document findings**

Create a temporary audit file:
```bash
echo "# crypto.js Audit" > /tmp/relay-audit.md
echo "Date: $(date)" >> /tmp/relay-audit.md
echo "## Findings" >> /tmp/relay-audit.md
```
Append findings (issues or "PASS").

---

### Task 2: Audit shared/relay-client.js for browser compatibility

**Files:**
- Read: `pages/shared/relay-client.js`

- [ ] **Step 1: Grep for problematic APIs**

```bash
cd /c/Users/n24q02m-wlap/projects/mcp-relay-core
grep -n "chrome\.\|webkit\|XMLHttpRequest\|document\.all\|navigator\.userAgent\|Buffer\.\|require(" pages/shared/relay-client.js
```
Expected: No matches.

- [ ] **Step 2: Verify Fetch API usage**

Read file and check:
- Uses `fetch()` (standard) not `XMLHttpRequest`
- No custom headers that might be blocked by CORS in certain browsers
- `AbortController` usage is standard (all modern browsers)
- JSON parsing uses `response.json()` (standard)

- [ ] **Step 3: Check polling / SSE / WebSocket patterns**

Verify:
- Polling uses `setInterval` or `setTimeout` (standard)
- No `EventSource` (SSE) without fallback
- No WebSocket without fallback
- Error handling covers network failures gracefully

- [ ] **Step 4: Check clipboard API**

```bash
grep -n "clipboard\|navigator\.clipboard\|execCommand" pages/shared/relay-client.js pages/*/form.js
```
- `navigator.clipboard.writeText` requires secure context (HTTPS) — production relay IS HTTPS, OK
- `document.execCommand('copy')` is deprecated but has wider compat — OK as fallback
- Verify no clipboard usage assumes success without try/catch

- [ ] **Step 5: Append findings to audit file**

---

### Task 3: Audit shared/style.css for browser compatibility

**Files:**
- Read: `pages/shared/style.css`

- [ ] **Step 1: Grep for vendor prefixes**

```bash
grep -n "\-webkit\-\|\-moz\-\|\-ms\-\|\-o\-" pages/shared/style.css
```
- Vendor prefixes are OK if paired with standard properties
- Flag if vendor prefix is used WITHOUT standard fallback

- [ ] **Step 2: Check for modern CSS features that need fallback**

Scan for:
- `gap` in flexbox (supported since 2021 in all browsers — OK)
- CSS custom properties `var(--` (supported everywhere — OK)
- `backdrop-filter` (may need `-webkit-` prefix for Safari — not relevant for Windows)
- `color-scheme` (OK, degrades gracefully)
- `:has()` selector (relatively new — verify not used)

```bash
grep -n ":has(\|backdrop-filter\|color-scheme\|container-type" pages/shared/style.css
```

- [ ] **Step 3: Append findings to audit file**

---

### Task 4: Audit 6 server-specific form.js files

**Files:**
- Read: `pages/wet/form.js`
- Read: `pages/mnemo/form.js`
- Read: `pages/code-review-graph/form.js`
- Read: `pages/telegram/form.js`
- Read: `pages/email/form.js`
- Read: `pages/notion/form.js`

- [ ] **Step 1: Grep all form.js for problematic patterns**

```bash
grep -rn "chrome\.\|webkit\|XMLHttpRequest\|document\.all\|navigator\.userAgent\|Buffer\.\|require(\|structuredClone\|crypto\.randomUUID" pages/*/form.js
```
- `structuredClone` — supported since 2022, OK for modern browsers
- `crypto.randomUUID` — supported since 2021, OK

- [ ] **Step 2: Check each form.js for DOM API compatibility**

For each file, verify:
- `document.getElementById` / `querySelector` (standard)
- `addEventListener` (standard)
- `FormData` (standard)
- `input.value` (standard)
- No `innerText` without `textContent` fallback (both standard now)

- [ ] **Step 3: Check telegram/form.js bidirectional messaging**

Telegram relay has special bidirectional messaging for OTP/2FA. Verify:
- Message polling uses standard Fetch
- Dynamic form field injection uses standard DOM APIs
- No browser-specific event handling

- [ ] **Step 4: Check email/form.js multi-account UI**

Email relay has custom multi-account form. Verify:
- Dynamic row creation uses standard DOM APIs
- CSV serialization is correct
- No browser-specific form validation

- [ ] **Step 5: Append findings to audit file**

---

### Task 5: Audit index.html files for compatibility

**Files:**
- Read: all 6 `pages/*/index.html`

- [ ] **Step 1: Check HTML doctype and meta tags**

Each file should have:
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
```

- [ ] **Step 2: Check script loading**

Verify:
- Scripts loaded with `<script src="...">` (not `type="module"` unless needed)
- Paths are absolute (`/shared/crypto.js`, `/shared/relay-client.js`) for Caddy proxy
- No `import` / `export` in non-module scripts
- Load order: crypto.js before relay-client.js before form.js

```bash
grep -n "script\|link.*css" pages/*/index.html
```

- [ ] **Step 3: Append findings to audit file**

---

### Task 6: Fix all issues found

- [ ] **Step 1: Review audit file**

Read `/tmp/relay-audit.md` and list all issues that need fixing.

- [ ] **Step 2: Fix each issue**

For each issue:
1. Edit the specific file
2. Ensure fix uses standard APIs
3. Test that fix doesn't break existing functionality

- [ ] **Step 3: Run existing tests**

```bash
cd /c/Users/n24q02m-wlap/projects/mcp-relay-core
bun test
```
Expected: All tests pass.

- [ ] **Step 4: Commit fixes**

```bash
git add -A
git commit -m "fix: ensure cross-browser compatibility for relay pages"
```

---

### Task 7: Manual browser test — Chrome

- [ ] **Step 1: Start relay server locally**

```bash
cd /c/Users/n24q02m-wlap/projects/mcp-relay-core
bun run packages/relay-server/src/index.ts
```
Or use deployed production: `https://<server>.n24q02m.com`

- [ ] **Step 2: Open each relay page in Chrome**

Open 6 URLs one by one:
1. `https://wet-mcp.n24q02m.com/relay` (hoac local equivalent)
2. `https://mnemo-mcp.n24q02m.com/relay`
3. `https://better-code-review-graph.n24q02m.com/relay`
4. `https://better-telegram-mcp.n24q02m.com/relay`
5. `https://better-email-mcp.n24q02m.com/relay`
6. `https://better-notion-mcp.n24q02m.com/relay`

- [ ] **Step 3: Verify per page**

Checklist per page:
- [ ] Page loads without JS errors (check DevTools Console)
- [ ] CSS renders correctly (no broken layout)
- [ ] All form fields visible and interactive
- [ ] Submit button triggers crypto + API call (check Network tab)
- [ ] Error states display correctly (submit without required field)
- [ ] For telegram: mode selector (Bot/User) switches fields

---

### Task 8: Manual browser test — Brave

- [ ] **Step 1: Open each relay page in Brave**

Repeat Task 7 Step 2-3 using Brave browser.

**Brave-specific checks:**
- Brave Shields may block fetch requests — verify relay API calls succeed
- If blocked, check if disabling Shields for the domain resolves it
- Document if Shields compatibility requires any code changes

---

### Task 9: Manual browser test — Edge

- [ ] **Step 1: Open each relay page in Edge**

Repeat Task 7 Step 2-3 using Edge browser.

Edge is Chromium-based so should match Chrome. Focus on verifying no regressions.

---

### Task 10: Run full relay-core test suite

- [ ] **Step 1: Run unit + integration tests**

```bash
cd /c/Users/n24q02m-wlap/projects/mcp-relay-core
bun test
```
Expected: All pass.

- [ ] **Step 2: Run Playwright E2E tests (if applicable)**

```bash
cd /c/Users/n24q02m-wlap/projects/mcp-relay-core
bun run test:e2e
```
Or the exact command from package.json.

- [ ] **Step 3: Fix any failures and re-run**

If failures, fix and repeat until all pass.

---

### Task 11: Release mcp-relay-core (if changes made)

- [ ] **Step 1: Check if any changes were committed**

```bash
cd /c/Users/n24q02m-wlap/projects/mcp-relay-core
git log --oneline HEAD...v1.2.0
```
If no commits since v1.2.0, skip this task.

- [ ] **Step 2: Push to main**

```bash
git push origin main
```

- [ ] **Step 3: Trigger CD workflow**

```bash
gh workflow run cd.yml
```

- [ ] **Step 4: Verify release**

```bash
gh run list --workflow=cd.yml --limit=1
```
Wait for success. Verify npm package updated.

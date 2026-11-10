# Engineering lessons

These entries were recovered from the working ledgers this repository kept at its root
until 2026-11-11: the notes of a discontinued automated assistant that proposed changes
under three remits -- performance (`bolt.md`), interface and accessibility
(`palette.md`) and security (`sentinel.md`). The entries are kept verbatim, each in the
shape it was written. The `**Commit:**` line under a heading names the commit that
landed that entry, so a settled question can be found in the repository history before
the same change is proposed again. A few entries quote the paths the ledgers occupied
before this move; those paths no longer exist.

# Performance (`bolt.md`)

Dates below are the dates the change landed on `main`, taken from `git log`.
Each entry carries the commit holding it, so an entry can be located in the
repository history before the same change is proposed again.

## 2026-07-18 - Everything under `plugins/` is generated; a patch there is erased at the next sync

**Commit:** 8999881
**Learning:** `plugins/<repo>/` is a mirror of a source repository, not source in its own right. `.github/workflows/cd.yml` runs on `repository_dispatch: plugin-sync` whenever one of the nine source repos publishes a release, and `scripts/sync-plugins.sh` rebuilds the tree with `rm -rf "$dst/$dir_name"` followed by `cp -r`. A patch applied to a mirrored file therefore survives only until that plugin's next release. This is not hypothetical: 7fce140 (2026-07-17) added ten lines of argument validation to `plugins/wet-mcp/skills/research-topic/scripts/run.py`, and 8999881 (2026-07-18) synced wet-mcp 3.6.0 and deleted all ten the following day. `CLAUDE.md` already carries the rule -- "Sync script pulls latest from source repos -- do not edit plugin files directly" -- and every proposal listed under Rejected below ignored it.
**Action:** Before proposing a change, check whether the file sits under `plugins/`. If it does, the change belongs in the source repository (`n24q02m/wet-mcp`, `n24q02m/agent-chat-plugin`, and so on), where it will be reviewed once and then reach this repository through the sync. The paths that are genuinely reviewable here are `scripts/`, `.github/`, `docs/`, and `.claude-plugin/marketplace.json`.

## 2026-07-18 - Hoisted the regexes in the agent-chat message scan

**Commit:** b16b816
**Learning:** `message_files` compiled `^(\d+)-` once per file through `re.match` with a literal pattern, and `slugify` recompiled `[^a-z0-9]+` on every call. Both run once per message per scan, and the scan runs on every `read`, `wait` poll and SessionStart hook, so the compile cache lookup was being paid in the one loop that repeats. Hoisting them to module level (`_SEQ_RE`, `_NON_ALNUM_RE`) also let the sort read `_seq_from_name` once per file instead of once per comparison.
**Action:** Hoist a pattern to module scope when the call site is inside a per-message loop. Note the caveat above: this commit edited a mirrored file, so it will not survive the next `agent-chat-plugin` sync unless the same change also exists upstream. That is an argument for making the change upstream first, not for repeating it here.

## 2026-07-25 - The frontmatter streaming read is already in the source repository

**Commit:** `agent-chat-plugin@ce79b70c` (source repository; not in this repository's history)
**Learning:** Replacing `path.read_text()` in `parse_frontmatter` with a line-by-line reader that stops at the closing `---` is a real improvement, and it was reviewed, measured and merged upstream on 2026-07-25 as "fix: parse frontmatter without reading the whole message". `n24q02m/agent-chat-plugin/.jules/bolt.md` carries the decision and asks that further proposals arrive with a measurement. Measured again here on this machine's real corpus (`$AGENT_CHAT_ROOT/*/*.md`, 82 messages, 165314 bytes, median message 1788 B, largest 7879 B), full sweep of all 82 files, minimum of 200 runs because eight other agents were contending for the disk and the median was unusable: 12.913 ms to 11.210 ms, a 1.703 ms saving, 13.2 percent, about 20.8 microseconds per file. Both implementations produced identical output on all 82 files. The saving is genuine but small at the sizes this repository actually sees; it only becomes decisive on bodies this corpus does not contain -- on a synthetic file with the same eight-line frontmatter the delta is -5.8 percent at a 2 KB body, -24.5 percent at 8 KB, -58.4 percent at 64 KB and -97.8 percent at 1 MB, because the old code's cost scales with the body it never uses while the new code's does not.
**Action:** The change is settled and lives upstream; the copy under `plugins/agent-chat-plugin/` picks it up at the next sync. Do not re-propose it here. For any future proposal on this path, quote a before-and-after measurement taken on this repository's own corpus, and use the minimum of at least 20 runs rather than the mean when the machine is busy.

## Rejected

Proposals that were reviewed and turned down, with the reason. They are recorded
here so the reason travels with the repository instead of staying behind in a
closed pull request.

### 2026-07-18 to 2026-07-31 - Fourteen rewrites of `parse_frontmatter` in the mirrored copy (#546, #547, #552, #553, #556, #560, #563, #567, #570, #576, #578, #582, #585, #587)
**Proposed:** replace `path.read_text()` in `plugins/agent-chat-plugin/chat.py` with a reader that stops at the closing `---`. One proposal per day for two weeks, each opened against a fresh branch with no reference to the previous thirteen.
**Why rejected:** not on the merits of the optimisation, which is sound and is recorded as accepted above. Two reasons. First, the file is a mirror; merging any of these would have been undone by the next `agent-chat-plugin` release exactly as 8999881 undid 7fce140. Second, the change is already in the source repository as of 2026-07-25, so the mirror converges on its own. The fourteen diffs never converged on each other either -- they alternate between `open(path, "r", ...)` and `path.open(...)`, between `line.strip()` and `line.rstrip("\r\n")`, and between assigning into `meta` directly and staging through a temporary dict -- which is what proposals generated without reading the previous ones look like.
**Action:** Check `git log` for the file and this ledger before opening a performance proposal. If the file is under `plugins/`, open it against the source repository instead.

### 2026-07-18 - Comments in source naming the tool and asserting an unmeasured speedup (#546 and others in the cluster)
**Proposed:** annotate the rewritten block with a comment naming the optimisation and the improvement it was expected to deliver.
**Why rejected:** this repository is public, and the comment asserted a benefit no measurement in the pull request supported. A note of that shape is noise for every later reader of the file, and it dates badly once the surrounding code moves.
**Action:** Write comments that explain why the code is shaped the way it is, in the voice of the surrounding file. Leave authorship to the commit metadata and the speedup to the commit message, where it can be checked against a number.

### 2026-07-28 to 2026-07-31 - Unrelated reformatting carried alongside the optimisation (#578, #585, #587)
**Proposed:** in the same diff as the frontmatter change, a blank line added after the module docstring of `plugins/agent-chat-plugin/hooks/session_inbox.py`, and in #587 a re-wrap of two decorators in `plugins/better-workspace-mcp/hooks/tests/test_check_credentials.py`.
**Why rejected:** neither file has anything to do with frontmatter parsing, and the second belongs to a different plugin entirely. Formatting churn in a mirrored tree is churn twice over: it cannot outlive the next sync, and it widens the diff a reviewer has to read to find the change the title describes.
**Action:** Keep the diff to the files the title names. Formatting of mirrored files is settled by the source repository's own formatter.

# Interface and accessibility (`palette.md`)

Dates below are the dates the change landed on `main`, taken from `git log`.
Each entry carries the commit holding it, so an entry can be located in the
repository history before the same change is proposed again.

## 2026-08-01 - What the Palette remit covers in this repository

**Commit:** (scope note; records no code change)
**Learning:** This repository is a marketplace and a documentation site, not an application, so "user interface" here means prose and metadata rather than components. The surfaces a reader actually meets are the Astro Starlight site under `docs/src/content/docs/` (`index.mdx`, `get-started/`, `reference/`), the per-plugin setup prose under `plugins/*/`, `README.md`, the descriptions and titles in `.claude-plugin/marketplace.json` that render in the plugin picker, and the messages the scripts in `scripts/` print when they fail. Those last two are easy to overlook and are the ones a user reads at the moment something has gone wrong.
**Action:** Direct Palette work at those paths. Note the boundary: `scripts/sync-plugins.sh` regenerates `plugins/<repo>/.claude-plugin/plugin.json`, `gemini-extension.json`, `skills/`, `hooks/`, `commands/` and `chat.py` from the source repositories, so wording inside those is fixed upstream and a change to it here is erased at that plugin's next release. The setup prose alongside them in `plugins/*/` is not regenerated and is edited here.

## 2026-08-01 - A conclusion that nothing needs changing is an entry, not a pull request

**Commit:** (scope note; records no code change)
**Learning:** #548 examined the Starlight docs, concluded there was no UX change worth making, and delivered that conclusion as a pull request changing no files, which then sat open for thirteen days. The conclusion may well have been right. The delivery was not: an empty pull request consumes a review cycle, runs the full check matrix, and leaves a branch to prune, all to communicate one sentence. `n24q02m/mnemo-mcp` reached the same conclusion three times the same way (#1003, #1007, #1032) before recording it in its own ledger.
**Action:** When a pass over the documentation finds nothing worth changing, write that here as a dated entry naming the surfaces examined, and open no pull request. A later pass can then start from what was already looked at instead of repeating it.

## Rejected

Proposals that were reviewed and turned down, with the reason. They are recorded
here so the reason travels with the repository instead of staying behind in a
closed pull request.

### 2026-07-18 - Empty pull request to create this journal (#544)
**Proposed:** initialise the Palette journal, delivered as a pull request changing no files (`+0/-0`).
**Why rejected:** rejected only in its delivered form. The request was right and this file is the answer to it, but the pull request contained no file. The reason is worth recording because it will catch the next attempt too: `.gitignore` ignores `.jules/` (three times over, at lines 6, 7 and 18, the last as `.Jules/`), so a newly created ledger is silently skipped by `git add` and the commit comes out empty. `.jules/sentinel.md` predates or bypassed that rule and is tracked, which is why editing it works while creating a sibling does not. wet-mcp and mnemo-mcp ignore `.jules/` as well and carry all three ledgers regardless, so the stack convention is to force the file into the index once; after that it is tracked and ordinary edits apply. This file and `bolt.md` were added with `git add -f`.
**Action:** To start a ledger here, `git add -f .jules/<name>.md` with its first entry already written. If a commit meant to add a file reports nothing to commit, check `git check-ignore -v` on the path before concluding there was nothing to say.

### 2026-07-19 - Empty pull request announcing that no change was needed (#548)
**Proposed:** report, as a pull request changing no files, that no UX enhancements were identified in the Starlight docs.
**Why rejected:** same shape as #544 and as mnemo #1003, #1007 and #1032. The finding belongs in this file, where the next pass will see it; in a closed pull request it is invisible to everything that reads the repository.
**Action:** Record the skip as the entry above does, naming the surfaces examined and the date, so the next pass can begin where this one stopped.

# Security (`sentinel.md`)

Dates below are the dates the change landed on `main`, taken from `git log`.
Each entry carries the commit holding it, so an entry can be located in the
repository history before the same finding is reported again.

## 2026-06-07 - Centralize MCP Hook Input Reading

**Commit:** 0d6cbfe
**Vulnerability:** Duplicated logic across multiple MCP hooks for reading JSON payloads from stdin (`sys.stdin.read(1024 * 1024)`), which parses user input and exits on failure. This creates a maintenance burden and increases the risk of inconsistencies or vulnerabilities (like DoS via unbounded reads or mishandled parsing) if one hook implements it differently.
**Learning:** Security mechanisms like bounded input reading and validation should be centralized into shared utility functions (e.g., `read_mcp_hook_input` in `mcp_common.py`) rather than copied and pasted across multiple entry points, adhering to the DRY principle and improving defense-in-depth consistency across the ecosystem.
**Prevention:** Centralize recurring security-critical logic, especially I/O handling and validation, into a shared `mcp_common.py` library and use it universally across all hooks to ensure uniform security controls.

## 2026-06-07 - Fix Path Traversal Vulnerability in marketplace scripts

**Commit:** d1e14f2
**Vulnerability:** Weak path traversal checks in `scripts/check_version_freshness.py` and `scripts/validate_marketplace.py` relied on `os.path.normpath` and `startswith("..")`, which could be bypassed via symlinks or absolute paths.
**Learning:** Robust path validation requires resolving paths fully using `os.path.realpath` and verifying that the resolved path is contained within the intended base directory using `os.path.commonpath`.
**Prevention:** Use a centralized `get_safe_path` utility for all file system operations involving user-supplied or external paths to ensure they remain within the project boundary.

## 2026-06-13 - Fix Token Leakage on Cross-Origin Redirects

**Commit:** 9c8a893
**Vulnerability:** The `scripts/check_version_freshness.py` script fetched GitHub API data using `urllib.request.urlopen` with a GitHub token in the `Authorization` header. If the API returned a redirect to a different domain, the default `HTTPRedirectHandler` passed the `Authorization` header to the new origin, creating an SSRF data-leakage risk.
**Learning:** Python's default `urllib` redirect handlers automatically forward all headers to the redirect target. Sensitive headers, particularly `Authorization` and `Cookie`, must be explicitly stripped when following cross-origin redirects to prevent token exfiltration.
**Prevention:** To prevent `Authorization` header leakage (SSRF) during HTTP redirects when using Python's `urllib.request`, the project uses a custom `NoAuthRedirectHandler` (inheriting from `urllib.request.HTTPRedirectHandler`) that explicitly strips sensitive headers like `Authorization` and `Cookie` when the redirect destination hostname differs from the original request hostname.

## 2026-06-18 - Hardening get_safe_path against multi-layered traversal

**Commit:** 62c5070
**Vulnerability:** Incomplete path traversal protection. Although the existing implementation used physical path resolution, it lacked lexical validation as defense-in-depth and did not explicitly reject null bytes, which could lead to inconsistent behavior or bypassed checks in certain environments.
**Learning:** Multi-layered path validation (null byte check -> lexical check -> physical check) ensures a "fail-closed" security posture. Lexical checks using `abspath` prevent traversal attempts using `..` components even before the target files exist, while physical checks using `realpath` prevent escaping via symlinks.
**Prevention:** Always combine lexical and physical path validation for any utility handling untrusted path inputs. Ensure all inputs are checked for null bytes before processing.

## 2026-06-21 - Mitigate Large Input Exhaustion DoS in MCP Hooks

**Commit:** 5dec249
**Vulnerability:** The centralized `read_mcp_hook_input` function in `mcp_common.py` previously read up to 1MB of data from `stdin`, which could expose the process to resource exhaustion via large payload processing.
**Learning:** Limiting untrusted input buffer sizes to the smallest functionally required size prevents malicious or malformed inputs from exhausting available memory and CPU resources. The previous 1MB limit was excessively large for standard JSON hook payloads.
**Prevention:** Reduce the maximum read limit from `stdin` to a conservative threshold (e.g., 64KB instead of 1MB) to proactively mitigate potential Denial of Service (DoS) vectors in execution environments.

## 2026-06-29 - Hardening get_safe_path against symlink+dotdot bypass

**Commit:** 2dc5f3b
**Vulnerability:** The `get_safe_path` utility was vulnerable to a path traversal bypass when a symlink was followed by a `..` component. This occurred because the function lexically simplified the path (removing `..`) before performing physical resolution, causing `os.path.realpath` to resolve the simplified path instead of following the symlink and then going up.
**Learning:** Physical path resolution with `os.path.realpath` must be performed on the original path components to correctly handle the interaction between symlinks and `..`. Lexical simplification (like `os.path.abspath` or `os.path.normpath`) should be used as a defense-in-depth layer but must not interfere with the physical resolution of the target path.
**Prevention:** Always resolve the physical path of the joined target by passing the raw sub-path to `os.path.realpath` relative to the resolved base directory.

## 2026-06-30 - Fix untrusted input in email subject and body via pull_request_target

**Commit:** 2fb15e3
**Vulnerability:** Untrusted data from PR/issue titles and bodies was directly interpolated into the subject and body of emails sent via GitHub Actions. This could lead to content injection or workflow manipulation if the input contained characters interpreted by the email action or the shell.
**Learning:** Never trust inputs from GitHub events (like issue/PR titles/bodies) directly in sensitive actions. Use a sanitization step (e.g., via Python) to clean and escape these inputs before using them as environment variables.
**Prevention:** Sanitize all untrusted inputs from GitHub events using a dedicated step that exports safe environment variables to `GITHUB_ENV`. Use secure delimiters for multi-line inputs.

## 2026-07-01 - Fix SSRF Token Leakage Bypass in NoAuthRedirectHandler

**Commit:** f9555e5
**Vulnerability:** The SSRF mitigation in `NoAuthRedirectHandler` (`scripts/check_version_freshness.py`) used `m.has_header` and `m.remove_header` to strip `Authorization` and `Cookie` headers across cross-origin redirects. However, Python's `urllib.request.Request.remove_header()` only removes the first matching header. If a sensitive header was injected redundantly with non-standard casing (e.g., `AUTHORIZATION`), the loop would miss it, causing token leakage to the third-party redirect target.
**Learning:** In Python's `urllib.request`, `remove_header` is insufficient for guaranteeing the total removal of sensitive headers because it stops at the first match and ignores redundancies.
**Prevention:** Always manually iterate over all keys in both `headers` and `unredirected_hdrs` and delete matches case-insensitively using `del` to guarantee complete header removal, effectively closing casing/redundancy bypasses.

## 2026-07-10 - Fix Path Traversal Bypass via Cached realpath

**Commit:** f99cdbd
**Vulnerability:** The `get_safe_path` utility cached base directory resolution (`os.path.realpath`) using `@functools.lru_cache` keyed purely by the string `base_dir`. This is vulnerable to cache poisoning/logic bugs if the underlying symlinks change or the process's Current Working Directory (CWD) changes. An attacker could exploit this by modifying a symlink after it was cached, bypassing path traversal mitigations.
**Learning:** Caching file system state operations like `os.path.abspath` or `os.path.realpath` using only string arguments is highly dangerous. Cached paths become invalid if CWD or underlying file system symlinks change, creating severe correctness and security bugs.
**Prevention:** Never use `@functools.lru_cache` to memoize file path resolution based on string values. Ensure that security checks rely on the actual, current state of the file system.

## 2026-07-17 - Input length limits on run.py: landed, then removed by the plugin sync

**Commit:** 7fce140, reverted by 8999881
**Vulnerability:** Reported as the `run.py` CLI wrapper for the `research-topic` skill lacking bounds on its arguments (query length, `--max-urls`, `--token-budget`).
**Learning:** This entry previously carried the date 2026-07-06 and read as a finding that had been fixed. It had not been, and the disagreement between this file and the code is what kept the finding alive. 7fce140 added ten lines of validation to `plugins/wet-mcp/skills/research-topic/scripts/run.py` on 2026-07-17. 8999881 synced wet-mcp 3.6.0 on 2026-07-18 and deleted all ten, because everything under `plugins/` is rebuilt from the source repository by `scripts/sync-plugins.sh`. Fourteen further reports followed, the first of them on the day of the deletion. On re-examination the finding does not hold on its merits either; the reasoning is in the Rejected section below.
**Prevention:** When a fix and a ledger entry disagree, trust the code. Before recording a fix under `plugins/`, confirm it landed in the source repository, because a fix applied only to the mirror is removed without notice and the entry left behind will either suppress a real finding or keep a false one alive.

## 2026-07-18 - Fix Path Traversal in agent-chat-plugin

**Commit:** 4fdb32f
**Vulnerability:** The `agent-chat-plugin/chat.py` script lacked validation for the `channel` and `task` inputs, allowing attackers to perform path traversal using `..`, `/`, `\`, or null bytes, potentially reading or overwriting files outside the intended `AGENT_CHAT_ROOT` directory.
**Learning:** Command-line inputs used to construct file paths must always be lexically validated to reject directory traversal characters (e.g., slashes, dots) before being joined with a base directory, even if the base directory is considered safe.
**Prevention:** Implement strict allowlisting or blocklisting for path components (e.g., rejecting null bytes, slashes, and `.`/`..`) before constructing paths from untrusted user input. Note that this fix was applied to the mirrored copy only. `n24q02m/agent-chat-plugin` grew its own `_check_safe_name` separately, and that version does not reject null bytes, so the next sync will replace the stricter check here with the weaker one upstream.

## Rejected

Findings that were reviewed and turned down, with the reason. They are recorded
here so the reason travels with the repository instead of staying behind in a
closed pull request.

### 2026-07-18 to 2026-07-31 - Bounding the `run.py` CLI arguments against resource exhaustion (#545, #549, #551, #554, #555, #561, #564, #566, #569, #575, #579, #583, #584, #588)
**Reported:** `plugins/wet-mcp/skills/research-topic/scripts/run.py` passes `query`, `--max-urls` and `--token-budget` to `run_agent` without bounds, allowing denial of service through a large `--max-urls` or an oversized query. Fourteen reports over fourteen days, each on a fresh branch, proposing between one and three `parser.error()` calls.
**Why rejected:** the bound already exists, one layer down, at the only consumer of these arguments. `wet_mcp.sources.agent_orchestrator.run_agent` calls `max_urls = _clamp_max_urls(max_urls)` before it does any work, and `_clamp_max_urls` is `min(max(int(max_urls), 1), _HARD_MAX_URLS)` with `_HARD_MAX_URLS = 20`. That clamp is what the CLI help text means by "default 5, cap 20": `--max-urls 100000` reaches the network as 20. The other two arguments do not carry the risk attributed to them. `token_budget` is a truncation ceiling rather than a driver of work; it is used only as `per_extract_chars = max(200, ((token_budget - 200) // max(len(extracts), 1)) * _CHARS_PER_TOKEN)`, which is passed to `_truncate_for_budget(body, per_extract_chars)`, so raising it truncates less of what was already fetched and cannot cause anything further to be fetched, while lowering it is floored at 200 characters. `query` is already rejected when empty, and otherwise lands in a single prompt string bounded by the operating system's argv limit and by the provider's own request limits. The threat model does not fit either: `run.py` is a skill wrapper run from a terminal by the operator, not a network-reachable endpoint, so the party supplying these arguments is the party the limits would protect against.
**Prevention:** Follow an argument into the function that consumes it before reporting it as unbounded, because validation absent at one layer is often enforced at the next. Where a limit is already documented in help text, check whether the enforcement exists elsewhere before adding a second copy of it. Note also the separate point recorded above: even a correct fix on this path could not persist here, because the file is a mirror of `n24q02m/wet-mcp` and is overwritten at that repository's next release.

### 2026-07-18 - Reformatting carried alongside a security report (#545)
**Reported:** together with the `run.py` change, a blank line inserted after the module docstring of `plugins/agent-chat-plugin/hooks/session_inbox.py`.
**Why rejected:** the file is unrelated to the finding and belongs to a different plugin, and like everything under `plugins/` it is regenerated by the sync. An unrelated edit in a security diff costs the reviewer the time it takes to prove it is unrelated, which is time taken from the finding itself.
**Prevention:** Keep a security diff to the code the finding names.

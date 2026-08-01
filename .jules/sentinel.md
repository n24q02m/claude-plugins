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

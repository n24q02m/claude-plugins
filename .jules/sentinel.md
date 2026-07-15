## 2024-06-03 - Centralize MCP Hook Input Reading
**Vulnerability:** Duplicated logic across multiple MCP hooks for reading JSON payloads from stdin (`sys.stdin.read(1024 * 1024)`), which parses user input and exits on failure. This creates a maintenance burden and increases the risk of inconsistencies or vulnerabilities (like DoS via unbounded reads or mishandled parsing) if one hook implements it differently.
**Learning:** Security mechanisms like bounded input reading and validation should be centralized into shared utility functions (e.g., `read_mcp_hook_input` in `mcp_common.py`) rather than copied and pasted across multiple entry points, adhering to the DRY principle and improving defense-in-depth consistency across the ecosystem.
**Prevention:** Centralize recurring security-critical logic, especially I/O handling and validation, into a shared `mcp_common.py` library and use it universally across all hooks to ensure uniform security controls.

## 2025-05-15 - Fix Path Traversal Vulnerability in marketplace scripts
**Vulnerability:** Weak path traversal checks in `scripts/check_version_freshness.py` and `scripts/validate_marketplace.py` relied on `os.path.normpath` and `startswith("..")`, which could be bypassed via symlinks or absolute paths.
**Learning:** Robust path validation requires resolving paths fully using `os.path.realpath` and verifying that the resolved path is contained within the intended base directory using `os.path.commonpath`.
**Prevention:** Use a centralized `get_safe_path` utility for all file system operations involving user-supplied or external paths to ensure they remain within the project boundary.

## 2024-06-12 - Fix Token Leakage on Cross-Origin Redirects
**Vulnerability:** The `scripts/check_version_freshness.py` script fetched GitHub API data using `urllib.request.urlopen` with a GitHub token in the `Authorization` header. If the API returned a redirect to a different domain, the default `HTTPRedirectHandler` passed the `Authorization` header to the new origin, creating an SSRF data-leakage risk.
**Learning:** Python's default `urllib` redirect handlers automatically forward all headers to the redirect target. Sensitive headers, particularly `Authorization` and `Cookie`, must be explicitly stripped when following cross-origin redirects to prevent token exfiltration.
**Prevention:** To prevent `Authorization` header leakage (SSRF) during HTTP redirects when using Python's `urllib.request`, the project uses a custom `NoAuthRedirectHandler` (inheriting from `urllib.request.HTTPRedirectHandler`) that explicitly strips sensitive headers like `Authorization` and `Cookie` when the redirect destination hostname differs from the original request hostname.

## 2026-06-13 - Hardening get_safe_path against multi-layered traversal
**Vulnerability:** Incomplete path traversal protection. Although the existing implementation used physical path resolution, it lacked lexical validation as defense-in-depth and did not explicitly reject null bytes, which could lead to inconsistent behavior or bypassed checks in certain environments.
**Learning:** Multi-layered path validation (null byte check -> lexical check -> physical check) ensures a "fail-closed" security posture. Lexical checks using `abspath` prevent traversal attempts using `..` components even before the target files exist, while physical checks using `realpath` prevent escaping via symlinks.
**Prevention:** Always combine lexical and physical path validation for any utility handling untrusted path inputs. Ensure all inputs are checked for null bytes before processing.

## 2025-06-20 - Mitigate Large Input Exhaustion DoS in MCP Hooks
**Vulnerability:** The centralized `read_mcp_hook_input` function in `mcp_common.py` previously read up to 1MB of data from `stdin`, which could expose the process to resource exhaustion via large payload processing.
**Learning:** Limiting untrusted input buffer sizes to the smallest functionally required size prevents malicious or malformed inputs from exhausting available memory and CPU resources. The previous 1MB limit was excessively large for standard JSON hook payloads.
**Prevention:** Reduce the maximum read limit from `stdin` to a conservative threshold (e.g., 64KB instead of 1MB) to proactively mitigate potential Denial of Service (DoS) vectors in execution environments.

## 2026-06-23 - Hardening get_safe_path against symlink+dotdot bypass
**Vulnerability:** The `get_safe_path` utility was vulnerable to a path traversal bypass when a symlink was followed by a `..` component. This occurred because the function lexically simplified the path (removing `..`) before performing physical resolution, causing `os.path.realpath` to resolve the simplified path instead of following the symlink and then going up.
**Learning:** Physical path resolution with `os.path.realpath` must be performed on the original path components to correctly handle the interaction between symlinks and `..`. Lexical simplification (like `os.path.abspath` or `os.path.normpath`) should be used as a defense-in-depth layer but must not interfere with the physical resolution of the target path.
**Prevention:** Always resolve the physical path of the joined target by passing the raw sub-path to `os.path.realpath` relative to the resolved base directory.

## 2026-06-29 - Fix untrusted input in email subject and body via pull_request_target
**Vulnerability:** Untrusted data from PR/issue titles and bodies was directly interpolated into the subject and body of emails sent via GitHub Actions. This could lead to content injection or workflow manipulation if the input contained characters interpreted by the email action or the shell.
**Learning:** Never trust inputs from GitHub events (like issue/PR titles/bodies) directly in sensitive actions. Use a sanitization step (e.g., via Python) to clean and escape these inputs before using them as environment variables.
**Prevention:** Sanitize all untrusted inputs from GitHub events using a dedicated step that exports safe environment variables to `GITHUB_ENV`. Use secure delimiters for multi-line inputs.

## 2026-07-03 - Fix Path Traversal Bypass via Cached realpath
**Vulnerability:** The `get_safe_path` utility cached base directory resolution (`os.path.realpath`) using `@functools.lru_cache` keyed purely by the string `base_dir`. This is vulnerable to cache poisoning/logic bugs if the underlying symlinks change or the process's Current Working Directory (CWD) changes. An attacker could exploit this by modifying a symlink after it was cached, bypassing path traversal mitigations.
**Learning:** Caching file system state operations like `os.path.abspath` or `os.path.realpath` using only string arguments is highly dangerous. Cached paths become invalid if CWD or underlying file system symlinks change, creating severe correctness and security bugs.
**Prevention:** Never use `@functools.lru_cache` to memoize file path resolution based on string values. Ensure that security checks rely on the actual, current state of the file system.

## 2026-07-01 - Fix SSRF Token Leakage Bypass in NoAuthRedirectHandler
**Vulnerability:** The SSRF mitigation in `NoAuthRedirectHandler` (`scripts/check_version_freshness.py`) used `m.has_header` and `m.remove_header` to strip `Authorization` and `Cookie` headers across cross-origin redirects. However, Python's `urllib.request.Request.remove_header()` only removes the first matching header. If a sensitive header was injected redundantly with non-standard casing (e.g., `AUTHORIZATION`), the loop would miss it, causing token leakage to the third-party redirect target.
**Learning:** In Python's `urllib.request`, `remove_header` is insufficient for guaranteeing the total removal of sensitive headers because it stops at the first match and ignores redundancies.
**Prevention:** Always manually iterate over all keys in both `headers` and `unredirected_hdrs` and delete matches case-insensitively using `del` to guarantee complete header removal, effectively closing casing/redundancy bypasses.

## 2024-07-16 - Enforce Input Bounds in argparse Scripts
**Vulnerability:** Scripts parsing CLI arguments via `argparse` (e.g., `run.py`) did not enforce input bounds, making them susceptible to Denial of Service (DoS) and resource exhaustion.
**Learning:** Relying solely on `argparse` type casting is insufficient for security. Explicitly enforcing input bounds (e.g., string lengths, numeric ranges) immediately after `parse_args()` is required to prevent resource exhaustion attacks.
**Prevention:** Always implement explicit boundary checks for parsed inputs to limit maximum string lengths and restrict numeric ranges before processing data.

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

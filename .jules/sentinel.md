## 2024-06-03 - Centralize MCP Hook Input Reading
**Vulnerability:** Duplicated logic across multiple MCP hooks for reading JSON payloads from stdin (`sys.stdin.read(1024 * 1024)`), which parses user input and exits on failure. This creates a maintenance burden and increases the risk of inconsistencies or vulnerabilities (like DoS via unbounded reads or mishandled parsing) if one hook implements it differently.
**Learning:** Security mechanisms like bounded input reading and validation should be centralized into shared utility functions (e.g., `read_mcp_hook_input` in `mcp_common.py`) rather than copied and pasted across multiple entry points, adhering to the DRY principle and improving defense-in-depth consistency across the ecosystem.
**Prevention:** Centralize recurring security-critical logic, especially I/O handling and validation, into a shared `mcp_common.py` library and use it universally across all hooks to ensure uniform security controls.

## 2025-05-15 - Fix Path Traversal Vulnerability in marketplace scripts
**Vulnerability:** Weak path traversal checks in `scripts/check_version_freshness.py` and `scripts/validate_marketplace.py` relied on `os.path.normpath` and `startswith("..")`, which could be bypassed via symlinks or absolute paths.
**Learning:** Robust path validation requires resolving paths fully using `os.path.realpath` and verifying that the resolved path is contained within the intended base directory using `os.path.commonpath`.
**Prevention:** Use a centralized `get_safe_path` utility for all file system operations involving user-supplied or external paths to ensure they remain within the project boundary.

## 2025-05-14 - Harden git subprocess calls in preserve-diacritics.py
**Vulnerability:** Unsafe subprocess call in preserve-diacritics.py allowed for potential option injection by not enforcing the -- separator for pathspecs.
**Learning:** Even with shell=False, git commands can be vulnerable to option injection if positional arguments are not strictly separated from options.
**Prevention:** Enforce -- separator for all pathspecs in git wrapper functions and make them keyword-only to prevent accidental positional misuse.

## 2024-06-03 - Centralize MCP Hook Input Reading
**Vulnerability:** Duplicated logic across multiple MCP hooks for reading JSON payloads from stdin (`sys.stdin.read(1024 * 1024)`), which parses user input and exits on failure. This creates a maintenance burden and increases the risk of inconsistencies or vulnerabilities (like DoS via unbounded reads or mishandled parsing) if one hook implements it differently.
**Learning:** Security mechanisms like bounded input reading and validation should be centralized into shared utility functions (e.g., `read_mcp_hook_input` in `mcp_common.py`) rather than copied and pasted across multiple entry points, adhering to the DRY principle and improving defense-in-depth consistency across the ecosystem.
**Prevention:** Centralize recurring security-critical logic, especially I/O handling and validation, into a shared `mcp_common.py` library and use it universally across all hooks to ensure uniform security controls.

## 2025-05-15 - Fix Path Traversal Vulnerability in marketplace scripts
**Vulnerability:** Weak path traversal checks in `scripts/check_version_freshness.py` and `scripts/validate_marketplace.py` relied on `os.path.normpath` and `startswith("..")`, which could be bypassed via symlinks or absolute paths.
**Learning:** Robust path validation requires resolving paths fully using `os.path.realpath` and verifying that the resolved path is contained within the intended base directory using `os.path.commonpath`.
**Prevention:** Use a centralized `get_safe_path` utility for all file system operations involving user-supplied or external paths to ensure they remain within the project boundary.

## 2026-06-10 - Secure Git Subprocess Calls in preserve-diacritics.py
**Vulnerability:** Unsafe construction of git command lines in `scripts/preserve-diacritics.py` could lead to option injection. While `--` was partially used, it wasn't enforced or correctly separated from command arguments in the `_run_git` wrapper.
**Learning:** Git command wrappers should use the `--` separator to explicitly distinguish options from pathspecs (filenames). Making pathspecs a keyword-only argument in the wrapper function enforces this separation at the API level and prevents accidental injection.
**Prevention:** Always use the `--` separator when passing filenames to git commands in subprocesses. Enforce keyword-only arguments for pathspecs in internal git wrappers to ensure consistent and secure command construction.

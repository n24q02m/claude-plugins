## 2024-05-24 - Centralized Hook Input Parsing
**Vulnerability:** Duplicated logic across multiple MCP pre-tool hooks for safely parsing JSON from `sys.stdin` with bounded reads (to prevent memory DoS).
**Learning:** Inconsistent implementation of security-critical standard I/O parsing across plugins could lead to future regressions or bypasses if one hook is updated but not others.
**Prevention:** Extracted the secure `sys.stdin` reading and parsing logic into a shared utility function (`read_mcp_hook_input`) in `mcp_common.py` to ensure uniform, safe bounded reads across all plugin hooks.

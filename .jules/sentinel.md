## 2025-05-15 - Robust Path Traversal Protection
**Vulnerability:** Weak path traversal checks in marketplace scripts used `os.path.normpath` and `startswith("..")`, which are context-dependent and bypassable with symlinks.
**Learning:** Robust protection requires resolving all components (symlinks/dots) via `os.path.realpath` and verifying the result remains under a trusted root via `os.path.commonpath`.
**Prevention:** Use a centralized `get_safe_path` utility anchored to a stable `PROJECT_ROOT` (derived from `__file__`) for all untrusted filesystem operations.

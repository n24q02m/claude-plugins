## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.
## 2025-02-12 - Replacing Python generator expressions with native evaluation
**Learning:** Using `str.endswith(tuple)` or `str.startswith(tuple)` is significantly more efficient and idiomatic in Python than using `any()` with a generator expression for multiple suffix or prefix matching. Replacing generator expressions within `any()` calls with explicit `for` loops improves performance for repeated `os.environ.get()` and `os.path.exists()` checks by avoiding generator overhead in Python hot paths.
**Action:** Always prefer explicit loop iterations or tuple support for string evaluations over `any(...)` or `all(...)` with generator expressions for core performance paths, since generator evaluation adds extra latency.
## 2025-02-12 - Replacing Subprocess with urllib for GitHub API Calls
**Learning:** Subprocess calls to `gh` CLI in a `ThreadPoolExecutor` are extremely expensive due to fork/exec overhead and CLI initialization. Using the standard library `urllib.request` to call the GitHub REST API directly significantly reduces overhead and allows for easy implementation of thread-safe in-memory caching.
**Action:** Replace external CLI subprocess calls with direct REST API requests using standard libraries like `urllib` or `requests` when performing high-frequency external lookups.
## 2025-02-12 - GitHub REST API tag name convention
**Learning:** Unlike the `gh` CLI which might use camelCase field names when requested via `--json tagName`, the GitHub REST API (`/releases/latest`) returns the tag name in a field called `tag_name` (snake_case).
**Action:** When migrating from `gh` CLI to direct REST API calls for GitHub releases, ensure field names are mapped correctly to the snake_case equivalents returned by the API.

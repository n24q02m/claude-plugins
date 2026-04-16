## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.
## 2025-02-12 - Replacing Python generator expressions with native evaluation
**Learning:** Using `str.endswith(tuple)` or `str.startswith(tuple)` is significantly more efficient and idiomatic in Python than using `any()` with a generator expression for multiple suffix or prefix matching. Replacing generator expressions within `any()` calls with explicit `for` loops improves performance for repeated `os.environ.get()` and `os.path.exists()` checks by avoiding generator overhead in Python hot paths.
**Action:** Always prefer explicit loop iterations or tuple support for string evaluations over `any(...)` or `all(...)` with generator expressions for core performance paths, since generator evaluation adds extra latency.
## 2025-05-15 - Parallelizing I/O-bound validation in scripts
**Learning:** For maintenance scripts that perform multiple I/O operations (like reading files) across a list of items, using `concurrent.futures.ThreadPoolExecutor` significantly reduces execution time compared to a sequential loop. This is especially effective when the number of items grows and the tasks are primarily waiting on I/O.
**Action:** Extract sequential processing logic into a standalone function and wrap it in a `ThreadPoolExecutor` for concurrent execution.

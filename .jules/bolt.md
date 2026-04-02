## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.

## 2026-04-02 - Optimized directory emptiness check in Bash
**Learning:** Checking for directory emptiness via `local files=("$dir"/*); [ ${#files[@]} -gt 0 ]` is O(N) in memory and time where N is the number of files in the directory. A more efficient O(1) approach uses native bash globbing with an early-return loop.
**Action:** Use `shopt -s nullglob dotglob; for _ in "$dir"/*; do shopt -u nullglob dotglob; return 0; done; shopt -u nullglob dotglob; return 1` for high-performance directory checks.

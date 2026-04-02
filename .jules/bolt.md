## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.
## 2025-05-14 - [performance improvement]
**Learning:** For shell script portability, performance, and avoiding SIGPIPE under 'set -euo pipefail', avoid slow subshells like 'find | head'. To check if a directory is empty with O(1) memory efficiency, avoid array assignments like 'local files=("$dir"/*)' and instead use an early-return loop with native Bash globbing: 'shopt -s nullglob dotglob; for _ in "$dir"/*; do shopt -u nullglob dotglob; return 0; done; shopt -u nullglob dotglob; return 1'.
**Action:** Use this pattern for all directory emptiness checks in shell scripts.

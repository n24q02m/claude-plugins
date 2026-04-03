## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.

## 2026-04-04 - Minimizing shopt state changes in loops
**Learning:** While native bash globbing is fast, repeatedly calling `shopt -s` and `shopt -u` inside a loop (e.g., thousands of times) adds measurable overhead due to state toggling.
**Action:** Move `shopt` configuration outside of hot loops in shell scripts whenever possible to achieve maximum performance.

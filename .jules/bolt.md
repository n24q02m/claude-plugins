## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.

## 2026-04-07 - Optimizing Loop Checks in GitHub Actions
**Learning:** Using `ls` or subshells within GitHub Actions `run` blocks for conditional checks inside loops can be inefficient and slightly slower than native Bash operations.
**Action:** Replace `ls` checks for directory contents with native Bash globbing loops and `break` to exit early when a file is found, improving performance in CD workflows.

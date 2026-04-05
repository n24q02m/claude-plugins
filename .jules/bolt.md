## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.

## 2024-05-29 - Avoiding 'ls' Subshells in Loops
**Learning:** Executing `ls` within a loop to check for directory content (e.g., `ls source/skills/*/SKILL.md >/dev/null 2>&1`) is inefficient because it spawns an external process for every check. Native Bash globbing with an early-return loop (`for _ in glob; do has_files=1; break; done`) is significantly faster and more resource-efficient in CI environments.
**Action:** Use native Bash globbing and `shopt -s nullglob` instead of `ls` to verify the existence of files matching a pattern in performance-critical sections.

## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.
## 2026-04-04 - Review Feedback: Balancing Security and Complexity
**Learning:** In this repository, preserving the simplicity and maintainability of the GitHub Actions workflow (using `jq` for JSON updates) was prioritized over implementing more verbose but supposedly more secure inline Python scripts. It is better to use `jq` properly (e.g., via `env` variables) than to introduce extensive new logic for single-line changes.
**Action:** Avoid replacing concise tool-based solutions (like `jq`) with verbose inline scripts unless a vulnerability is proven and cannot be mitigated using the existing tools.

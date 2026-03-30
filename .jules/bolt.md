## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.

## 2024-05-29 - Memory-Efficient Directory Checks in Bash
**Learning:** While native bash globbing avoids subshell penalties, assigning the glob to an array (`local files=("$dir"/*)`) forces an additional O(N) memory allocation for large directories, which can be slow and crash for thousands of files. While the glob itself still evaluates the full directory listing before the loop begins, we can skip allocating a massive array variable by using an early-return loop.
**Action:** Use an early-return loop (`for _ in "$dir"/*; do return 0; done`) to avoid secondary O(N) memory allocation when checking if a directory is empty in Bash.

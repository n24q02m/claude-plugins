## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.

## 2024-05-29 - O(1) Memory Directory Content Checks in Bash
**Learning:** Checking directory emptiness with `local files=("$dir"/*)` allocates an array for all files, which causes a spike in memory (O(N)) and execution time for large directories with many files.
**Action:** Replace array assignment with an early-return bash loop `for _ in "$dir"/*; do ... return 0; done` to check if a directory has files in O(1) memory and time.

## 2026-03-27 - [PERFORMANCE] Shell script directory emptiness checks
**Learning:** Using `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` to check if a directory is empty requires spawning subshells and external processes (`find` and `head`), which is significantly slower in loops.
**Action:** Use native Bash array globbing instead: `shopt -s nullglob dotglob; local files=("$dir"/*); shopt -u nullglob dotglob; [ ${#files[@]} -gt 0 ]` to avoid process forks entirely.

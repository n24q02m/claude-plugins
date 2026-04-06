## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.

## 2024-05-28 - Faster File System Traversal in Python
**Learning:** Using `os.listdir()` requires additional `os.path` evaluations (like `os.path.isdir()` or `os.path.join()`) to work with files and directories. `os.scandir()` returns an iterator of `DirEntry` objects, which reduces system calls by caching file attributes and providing immediate access to `.name` and `.path`.
**Action:** Replace `os.listdir()` with `os.scandir()` for file system traversals in Python scripts to optimize performance.

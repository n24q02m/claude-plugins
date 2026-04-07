## 2024-05-28 - Fast Empty Directory Checks in Bash
**Learning:** Using subshells with `find | head -n 1` to check if a directory is empty in shell scripts is extremely slow compared to native bash globbing (`shopt -s nullglob dotglob; local files=("$dir"/*); ...`). Subshells incur a huge performance penalty when executed repeatedly in loops.
**Action:** Replace `[ -n "$(find "$dir" -mindepth 1 2>/dev/null | head -n 1)" ]` with a `has_files()` function using bash globs to dramatically speed up directory checking.

## 2026-04-05 - Optimize Marketplace Validation Directory Traversal
**Learning:** Using `os.scandir()` instead of `os.listdir()` in `scripts/validate_marketplace.py` improves performance in the plugin validation loop because `scandir` yields `DirEntry` objects which contain pre-fetched attributes (like `is_dir()`), reducing the number of system calls needed during traversal of multiple plugin skill directories.
**Action:** Always prefer `os.scandir()` or `pathlib.Path.iterdir()` over `os.listdir()` when checking file types or attributes during directory iteration.

## 2026-04-05 - Optimize Marketplace Validation Directory Traversal
**Learning:** Using `os.scandir()` instead of `os.listdir()` in `scripts/validate_marketplace.py` improves performance in the plugin validation loop because `scandir` yields `DirEntry` objects which contain pre-fetched attributes (like `is_dir()`), reducing the number of system calls needed during traversal of multiple plugin skill directories.
**Action:** Always prefer `os.scandir()` or `pathlib.Path.iterdir()` over `os.listdir()` when checking file types or attributes during directory iteration.

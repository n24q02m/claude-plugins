## 2025-05-14 - Parallelize Plugin Validation

**Learning:** Sequential I/O in a loop (N+1 pattern) can significantly slow down scripts as the number of items grows. Refactoring the loop body into a standalone function makes it easy to parallelize using `ThreadPoolExecutor`.

**Action:** Identify I/O-bound loops and refactor them to use `concurrent.futures.ThreadPoolExecutor` for improved performance.

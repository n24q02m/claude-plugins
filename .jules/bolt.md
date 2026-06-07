## 2025-03-03 - Parallelizing Plugin Validation
**Learning:** Parallelizing I/O-bound validation tasks (like checking multiple plugin directories and files) using `ThreadPoolExecutor` significantly reduces total execution time when dealing with multiple plugins.
**Action:** Identify N+1 patterns in file I/O operations within loops and use `concurrent.futures.ThreadPoolExecutor` to process them concurrently.

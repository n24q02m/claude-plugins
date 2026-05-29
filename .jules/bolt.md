## 2024-05-29 - Parallelize I/O-Bound Plugin Validation
**Learning:** In `scripts/validate_marketplace.py`, synchronous, sequential file reading and directory traversal per plugin introduce a significant I/O bottleneck, as testing each plugin involves multiple disk access operations.
**Action:** Extract per-plugin logic and use `concurrent.futures.ThreadPoolExecutor` with `max_workers=10` to process I/O-bound validation checks in parallel.

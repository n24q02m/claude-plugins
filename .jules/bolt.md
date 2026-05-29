## 2024-05-29 - Parallelize I/O-bound validation
**Learning:** In `scripts/validate_marketplace.py`, plugin validation sequentially reads multiple files (`plugin.json`, `gemini-extension.json`, `SKILL.md`) for each plugin. This repeated synchronous I/O operations create a bottleneck.
**Action:** Parallelize I/O-bound tasks using `concurrent.futures.ThreadPoolExecutor` with `max_workers=10` to mitigate the performance impact of repeated synchronous file reads and directory traversals.

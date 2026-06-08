
## 2025-05-14 - Add Caching to Relay Configuration Checks
**Learning:** Caching frequently used configuration checks that involve I/O (like environment variable lookups and file system existence checks) can significantly reduce overhead during process execution. However, caching introduces global state that must be explicitly managed in test suites using `cache_clear()` to maintain test isolation.
**Action:** Always use `@functools.lru_cache` for idempotent I/O operations that are expected to be stable during a single execution, and ensure corresponding unit tests call `cache_clear()` in their `setUp` methods.

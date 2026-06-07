## 2025-05-15 - Caching Relay Configuration
**Learning:** Configuration checks that involve filesystem I/O and environment variable lookups can be significantly optimized by caching the result when the state is unlikely to change during execution.
**Action:** Always consider using `@functools.lru_cache()` for filesystem-based configuration checks in MCP servers and hooks.

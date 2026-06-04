## 2025-05-14 - Missing Caching for Relay Configuration Checks

**💡 What:** Implemented `@functools.lru_cache(maxsize=1)` for the `is_relay_configured` function in `plugins/mcp_common.py`.

**🎯 Why:** The relay configuration state (existence of `config.enc`) rarely changes during the execution of a script or single server hook. Repeatedly checking the filesystem is inefficient.

**📊 Impact:** Subsequent calls to `is_relay_configured` now execute in O(1) time without filesystem I/O.

**🔬 Measurement:** Verified by adding `.cache_clear()` calls to the test suite, ensuring that tests correctly verify both positive and negative configuration states by bypassing the cache when needed.

## 2025-06-04 - Fix missing tests for run.py error path

**Vulnerability:** N/A (Performance/Testing task)
**Learning:** Testing CLI scripts that use lazy imports and dynamic paths requires careful mocking of the modules being imported. Using `sys.modules` to mock a package before importing the script that uses it is an effective way to avoid `ModuleNotFoundError` during unit tests.
**Prevention:** Always include tests for both success and error paths in CLI wrappers to ensure deterministic failure detection.

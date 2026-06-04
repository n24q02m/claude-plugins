## 2026-06-04 - [FIX] Broad Exception Handling
**Vulnerability:** Broad Exception Handling
**Learning:** Catching Exception broadly can hide unexpected bugs. Always catch specific exceptions when possible.
**Prevention:** Use specific exception types like json.JSONDecodeError instead of the base Exception class.

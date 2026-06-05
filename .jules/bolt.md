## 2025-02-27 - Pre-compiling regex in diff parsing loops
**💡 What:** Pre-compiled the hunk header regex `_HUNK_HEADER_RE` at the module level in `scripts/preserve-diacritics.py`.
**🎯 Why:** Calling `re.match()` with an inline pattern inside a tight loop (like diff line parsing) incurs cache lookup overhead. Pre-compiling the regex avoids this overhead completely.
**📊 Impact:** Eliminates regex cache lookup overhead for every line of a diff parsed by the hook.
**🧪 Measurement:** Verified performance and correctness by running the repository's test suite, including `test_preserve_diacritics.py`.

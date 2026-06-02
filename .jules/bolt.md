## 2024-06-25 - Diff Parsing Performance

**Learning:** In tight parsing loops that process line-by-line tool output (like `git diff`), calling `re.match` with an inline string pattern creates measurable cache lookup overhead in Python, even if the regex string is small.

**Action:** Always pre-compile `re` objects at the module level using `re.compile()` for regexes used within tight loop iterations.

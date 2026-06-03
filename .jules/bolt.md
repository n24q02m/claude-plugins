## 2024-05-23 - Pre-compiling regex in I/O bound loops
**Learning:** Calling `re.match()` with inline string patterns repeatedly inside tight I/O-bound loops (like diff parsing) incurs measurable cache lookup overhead in Python, even though the regex is internally cached.
**Action:** Pre-compile regular expressions using `re.compile()` at the module level when they are used within high-frequency loops. This explicitly eliminates the runtime lookup penalty and improves performance, as demonstrated by pre-compiling `_HUNK_RE` in the diff hook which sped up execution.

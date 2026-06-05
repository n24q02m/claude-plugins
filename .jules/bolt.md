## 2024-06-05 - Avoid list comprehensions for counting
**Learning:** In Python, using `[c for c in sequence if condition]` solely to check the length of the resulting list introduces unnecessary O(N) space complexity by allocating intermediate lists in memory, which is inefficient for large inputs like git diffs.
**Action:** Replace length-checking list comprehensions with generator expressions wrapped in `sum()`, such as `sum(1 for c in sequence if condition)`. This reduces space complexity to O(1) while maintaining O(N) time complexity.

## 2024-06-05 - Pre-compile regex in high-frequency loops
**Learning:** Calling `re.match()` with a string pattern inside a loop relies on Python's internal regex cache. While fast, for high-frequency loops (like processing every line of a git diff), the cache lookup still incurs overhead.
**Action:** Always pre-compile regular expressions using `re.compile()` at the module level when they are used inside tight, high-frequency loops.

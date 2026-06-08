## 2026-06-08 - Optimize Vietnamese diacritic counting
**Learning:** List comprehensions allocate O(N) memory even if only the count is needed. `sum()` with a generator expression is O(1) space.
**Action:** Use `sum(1 for c in s if c in targets)` for character counting.

## 2025-05-24 - Optimize Vietnamese diacritic counting
**Optimization:** Replaced list comprehensions with generator expressions in `sum()` for character counting.
**Impact:** Reduced space complexity from O(N) to O(1) by avoiding intermediate list allocations.
**Verification:** Passed existing tests and manually verified logic.

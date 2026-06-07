## 2024-06-07 - Optimize character counting memory overhead
**Learning:** Using list comprehensions `[c for c in s if c in targets]` just to count the frequency of target characters allocates an unnecessary intermediate list, yielding O(N) space complexity instead of O(1).
**Action:** Replace list comprehensions used only for length/counting with generator expressions inside `sum()` (e.g., `sum(1 for c in s if c in targets)`).

## 2025-05-14 - Redundant String Scanning for Unicode Replacement
**Learning:** Chaining `in` checks on a dictionary in a loop can be optimized by using `set.intersection()` when dealing with character sets, reducing O(N*M) complexity.
**Action:** Always check if a pre-calculated set intersection can replace iterative string containment checks.

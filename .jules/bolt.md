## 2026-06-07 - Optimize Character Counting in preserve-diacritics.py
**Learning:** Using list comprehensions for character counting in loops allocates memory unnecessarily.
**Action:** Replace list comprehensions with generator expressions inside `sum()` for O(1) space complexity when only the count is needed.

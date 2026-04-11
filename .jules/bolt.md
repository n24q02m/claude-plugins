## 2024-04-11 - Pre-compile regular expressions in scripts

**Learning:** Re-evaluating inline regular expressions like `re.match(r"^[a-zA-Z0-9_-]+$", name)` within loops forces Python to repeatedly perform cache lookups inside the `re` module, causing unnecessary overhead.

**Action:** Always pre-compile regular expressions at the global module level using `re.compile()` (e.g., `NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")`) when they are used within tight loops or frequently executed functions to eliminate the cache lookup overhead.

## 2024-05-30 - Module-level Regex Compilation for Loop Iterations
**Learning:** Relying on `re.match` with an inline string inside an I/O-bound loop like diff parsing incurs cache lookup overhead for the regex pattern. Pre-compiling the regex at the module level significantly boosts performance.
**Action:** Always pre-compile regexes at the module scope when used within high-frequency loops.

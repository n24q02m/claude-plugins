import time
import re
import functools

# Test 1: Python's internal re cache
start = time.time()
for _ in range(100000):
    re.search("^[a-z]+$", "hello")
print(f"re.search: {time.time() - start}")

# Test 2: @functools.lru_cache helper
@functools.lru_cache(maxsize=128)
def _cached_re_compile(pattern: str):
    return re.compile(pattern)

start = time.time()
for _ in range(100000):
    _cached_re_compile("^[a-z]+$").search("hello")
print(f"_cached_re_compile: {time.time() - start}")

# Test 3: Module level compile
_PATTERN = re.compile("^[a-z]+$")
start = time.time()
for _ in range(100000):
    _PATTERN.search("hello")
print(f"module level: {time.time() - start}")

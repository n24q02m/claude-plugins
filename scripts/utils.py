import os
import re
import functools


def sanitize_log(msg: str) -> str:
    """Sanitize strings for GitHub Actions log commands."""
    return str(msg).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


# Optimization: Memoize the base_dir path resolution since validate_marketplace
# runs in parallel with the same base_dir for all plugins. This reduces
# redundant os.path.abspath and os.path.realpath syscalls.
@functools.lru_cache(maxsize=16)
def _get_base_paths(base_dir: str) -> tuple[str, str]:
    abs_base = os.path.abspath(base_dir)
    real_base = os.path.realpath(abs_base)
    return abs_base, real_base


def get_safe_path(base_dir: str, sub_path: str) -> str:
    """
    Resolve sub_path relative to base_dir and ensure it remains within base_dir.

    This function provides multi-layered protection against path traversal:
    1. Null byte check: Rejects paths containing null characters.
    2. Lexical check: Rejects obvious traversal attempts even before physical resolution.
    3. Physical check: Ensures the resolved real path is within base_dir (using realpath).
       Crucially, it resolves the path without prior lexical simplification to correctly
       handle symlinks followed by '..' components.
    """
    if "\0" in base_dir or "\0" in sub_path:
        raise ValueError("Path contains null bytes")

    # Layer 1: Lexical check (defense-in-depth)
    # This prevents simple traversal using '..' even if the files don't exist yet.
    abs_base, real_base = _get_base_paths(base_dir)
    abs_target = os.path.abspath(os.path.join(abs_base, sub_path))
    if os.path.commonpath([abs_base, abs_target]) != abs_base:
        raise ValueError("Path traversal detected (lexical)")

    # Layer 2: Physical check
    # Resolve the real path of the base and the target.
    # We resolve the target by joining it with the real base to ensure symlinks
    # are followed correctly and '..' components are resolved physically.
    real_target = os.path.realpath(os.path.join(real_base, sub_path))

    if os.path.commonpath([real_base, real_target]) != real_base:
        raise ValueError("Path traversal detected (physical)")

    return os.path.relpath(real_target, real_base)


# Pre-compile regex at module level to avoid cache lookup overhead
PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")

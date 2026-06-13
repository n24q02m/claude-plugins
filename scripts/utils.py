import functools
import os
import re


@functools.lru_cache(maxsize=None)
def _cached_realpath(path: str) -> str:
    """Cached version of os.path.realpath to avoid repeated resolution of identical paths."""
    return os.path.realpath(path)


def sanitize_log(msg: str) -> str:
    """Sanitize strings for GitHub Actions log commands."""
    return str(msg).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def get_safe_path(base_dir: str, sub_path: str) -> str:
    """Resolve sub_path relative to base_dir and ensure it remains within base_dir."""
    abs_base = _cached_realpath(base_dir)
    abs_target = os.path.realpath(os.path.join(abs_base, sub_path))
    if os.path.commonpath([abs_base, abs_target]) != abs_base:
        raise ValueError("Path traversal detected")
    return os.path.relpath(abs_target, abs_base)


# Pre-compile regex at module level to avoid cache lookup overhead
PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")

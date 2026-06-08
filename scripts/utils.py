import os
import re

# Resolve the project root directory once at module level
PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), ".."))


def sanitize_log(msg: str) -> str:
    """Sanitize strings for GitHub Actions log commands."""
    return str(msg).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def get_safe_path(untrusted_path: str, base_dir: str = None) -> str:
    """
    Resolve untrusted_path relative to base_dir and ensure it remains within base_dir.
    Defaults to PROJECT_ROOT if base_dir is not provided.
    """
    if base_dir is None:
        base_dir = PROJECT_ROOT
    abs_base = os.path.realpath(base_dir)
    abs_target = os.path.realpath(os.path.join(abs_base, untrusted_path))
    if os.path.commonpath([abs_base, abs_target]) != abs_base:
        raise ValueError("Path traversal detected")
    return abs_target


# Pre-compile regex at module level to avoid cache lookup overhead
PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")

import os
import re

# Centralized project root derived from the script location
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def get_safe_path(untrusted_path: str, base_dir: str = None) -> str:
    """
    Safely resolve a path and ensure it remains within the base_dir.
    Resolves symlinks and '..' components.
    Returns the absolute path if safe, otherwise raises ValueError.
    """
    if base_dir is None:
        base_dir = PROJECT_ROOT
    abs_base = os.path.realpath(base_dir)
    # Join and resolve to absolute path (handling symlinks and '..')
    abs_target = os.path.realpath(os.path.join(abs_base, untrusted_path))

    # Verify the resolved path is still within abs_base
    if os.path.commonpath([abs_base, abs_target]) != abs_base:
        raise ValueError(
            f"Path traversal detected: {untrusted_path} resolves outside {base_dir}"
        )

    return abs_target


def sanitize_log(msg: str) -> str:
    """Sanitize strings for GitHub Actions log commands."""
    return str(msg).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


# Pre-compile regex at module level to avoid cache lookup overhead
PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")

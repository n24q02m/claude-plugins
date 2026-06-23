#!/usr/bin/env python3
"""Validate marketplace.json structure and plugin integrity."""

import itertools
import concurrent.futures
import json
import os
import sys

from utils import sanitize_log, PLUGIN_NAME_PATTERN, get_safe_path


def _validate_plugin_name(plugin: dict) -> tuple[str, list[str]]:
    """Validate plugin name and return it with any errors found."""
    errors = []
    name = plugin.get("name")

    if name is None:
        name = "Unknown"
    elif not isinstance(name, str):
        errors.append(f"Plugin {sanitize_log(str(name))}: name must be a string")
        return "Unknown", errors

    if not PLUGIN_NAME_PATTERN.fullmatch(name):
        errors.append(
            f"Plugin {name}: invalid name format (must match ^[a-zA-Z0-9-]+$)"
        )

    return name, errors


def _validate_plugin_source(
    name: str, plugin: dict, base_dir: str
) -> tuple[str | None, list[str]]:
    """Validate plugin source and return resolved plugin_dir with any errors."""
    errors = []
    source = plugin.get("source")
    if source is None:
        errors.append(f"Plugin {name}: missing source")
        return None, errors

    if not isinstance(source, str):
        errors.append(f"Plugin {name}: source must be a string")
        return None, errors

    # Security check: prevent path traversal
    try:
        plugin_dir = get_safe_path(base_dir, source)
        return plugin_dir, errors
    except (OSError, ValueError):
        errors.append(f"Plugin {name}: invalid source path (path traversal blocked)")
        return None, errors


def _validate_plugin_json(name: str, plugin_dir: str) -> tuple[list[str], bool]:
    """Validate plugin.json and return errors and whether to continue validation."""
    errors = []
    pjson = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    # Optimization: Use EAFP to avoid redundant os.path.exists stat syscalls before open
    try:
        with open(pjson, encoding="utf-8") as f:
            pdata = json.load(f)
        # Optimization: Use tuple literal over list literal for slight interpreter-level improvement
        for req in ("name", "description", "mcpServers"):
            if req not in pdata:
                errors.append(f"{name}: plugin.json missing {req}")
        return errors, True
    except FileNotFoundError:
        errors.append(f"{name}: missing {pjson}")
        return (
            errors,
            False,
        )  # Stop checking files if the directory/plugin.json is missing
    except Exception as e:
        errors.append(f"{name}: Failed to parse {pjson}: {e}")
        return errors, True


def _validate_gemini_extension(name: str, plugin_dir: str) -> list[str]:
    """Validate gemini-extension.json and return any errors found."""
    errors = []
    gext = os.path.join(plugin_dir, "gemini-extension.json")
    # Optimization: Use EAFP to avoid redundant os.path.exists stat syscalls before open
    try:
        with open(gext, encoding="utf-8") as f:
            gdata = json.load(f)
        if "version" not in gdata:
            errors.append(f"{name}: gemini-extension.json missing version")
    except FileNotFoundError:
        pass
    except Exception as e:
        errors.append(f"{name}: Failed to parse {gext}: {e}")
    return errors


def _validate_skills(name: str, plugin_dir: str) -> list[str]:
    """Validate plugin skills and return any errors found."""
    errors = []
    skills_dir = os.path.join(plugin_dir, "skills")
    # Optimization: Use EAFP to avoid redundant os.path.isdir stat syscalls before os.scandir
    try:
        with os.scandir(skills_dir) as entries:
            for entry in entries:
                if entry.is_dir():
                    skill_name = entry.name
                    skill_file = os.path.join(entry.path, "SKILL.md")
                    # Optimization: Use EAFP to avoid redundant os.path.exists stat syscalls before open
                    try:
                        with open(skill_file, encoding="utf-8") as f:
                            # Optimization: read only first 100 characters for partial check
                            content = f.read(100)
                        if not content.startswith("---"):
                            errors.append(
                                f"{name}/skills/{skill_name}: SKILL.md missing frontmatter"
                            )
                        if len(content.strip()) < 50:
                            errors.append(
                                f"{name}/skills/{skill_name}: SKILL.md too short"
                            )
                    except FileNotFoundError:
                        pass
                    except Exception as e:
                        errors.append(
                            f"{name}/skills/{skill_name}: Failed to read SKILL.md: {e}"
                        )
    except (FileNotFoundError, NotADirectoryError):
        pass
    return errors


def _validate_plugin(plugin: dict, base_dir: str) -> list[str]:
    """Helper function to validate a single plugin, returns list of error messages."""
    name, name_errors = _validate_plugin_name(plugin)
    if any("name must be a string" in e for e in name_errors):
        return name_errors

    plugin_dir, source_errors = _validate_plugin_source(name, plugin, base_dir)
    all_errors = name_errors + source_errors

    if not plugin_dir:
        return all_errors

    json_errors, should_continue = _validate_plugin_json(name, plugin_dir)
    all_errors.extend(json_errors)

    if not should_continue:
        return all_errors

    all_errors.extend(_validate_gemini_extension(name, plugin_dir))
    all_errors.extend(_validate_skills(name, plugin_dir))

    return all_errors


def validate_marketplace():
    """Validate marketplace.json and all referenced plugins."""
    errors = []

    try:
        with open(".claude-plugin/marketplace.json", encoding="utf-8") as f:
            marketplace = json.load(f)
    except Exception as e:
        print(f"::error ::{sanitize_log(f'Failed to load marketplace.json: {e}')}")
        sys.exit(1)

    required = ["name", "metadata", "owner", "plugins"]
    for field in required:
        if field not in marketplace:
            errors.append(f"marketplace.json: Missing field: {field}")

    if "plugins" in marketplace:
        plugins = marketplace["plugins"]
        if not plugins:
            errors.append("marketplace.json: No plugins defined")

        # Optimization: use ThreadPoolExecutor to parallelize I/O bound plugin validation checks
        base_dir = os.getcwd()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Flatten lists of errors from futures
            for plugin_errors in executor.map(
                _validate_plugin, plugins, itertools.repeat(base_dir)
            ):
                errors.extend(plugin_errors)

    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"::error ::{sanitize_log(e)}")
        sys.exit(1)
    else:
        num_plugins = len(marketplace.get("plugins", []))
        print(f"All {num_plugins} plugins validated successfully")


if __name__ == "__main__":
    validate_marketplace()

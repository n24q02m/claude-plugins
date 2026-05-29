#!/usr/bin/env python3
"""Validate marketplace.json structure and plugin integrity."""

import concurrent.futures
import json
import os
import sys

from utils import sanitize_log, PLUGIN_NAME_PATTERN


def validate_plugin(plugin):
    """Validate a single plugin's integrity."""
    plugin_errors = []
    name = plugin.get("name")
    if name is None:
        name = "Unknown"
    elif not isinstance(name, str):
        plugin_errors.append(f"Plugin {sanitize_log(str(name))}: name must be a string")
        return plugin_errors

    if not PLUGIN_NAME_PATTERN.fullmatch(name):
        plugin_errors.append(
            f"Plugin {name}: invalid name format (must match ^[a-zA-Z0-9-]+$)"
        )
        return plugin_errors

    source = plugin.get("source")
    if source is None:
        plugin_errors.append(f"Plugin {name}: missing source")
        return plugin_errors

    if not isinstance(source, str):
        plugin_errors.append(f"Plugin {name}: source must be a string")
        return plugin_errors

    # Security check: prevent path traversal
    norm_source = os.path.normpath(source)
    if os.path.isabs(norm_source) or norm_source.startswith(".."):
        plugin_errors.append(
            f"Plugin {name}: invalid source path (path traversal blocked)"
        )
        return plugin_errors

    plugin_dir = norm_source

    # Check plugin.json exists and is valid
    pjson = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    # Optimization: Use EAFP to avoid redundant os.path.exists stat syscalls before open
    try:
        with open(pjson, encoding="utf-8") as f:
            pdata = json.load(f)
        # Optimization: Use tuple literal over list literal for slight interpreter-level improvement
        for req in ("name", "description", "mcpServers"):
            if req not in pdata:
                plugin_errors.append(f"{name}: plugin.json missing {req}")
    except FileNotFoundError:
        plugin_errors.append(f"{name}: missing {pjson}")
        return plugin_errors
    except Exception as e:
        plugin_errors.append(f"{name}: Failed to parse {pjson}: {e}")

    # Check gemini-extension.json has version (optional file)
    gext = os.path.join(plugin_dir, "gemini-extension.json")
    # Optimization: Use EAFP to avoid redundant os.path.exists stat syscalls before open
    try:
        with open(gext, encoding="utf-8") as f:
            gdata = json.load(f)
        if "version" not in gdata:
            plugin_errors.append(f"{name}: gemini-extension.json missing version")
    except FileNotFoundError:
        pass
    except Exception as e:
        plugin_errors.append(f"{name}: Failed to parse {gext}: {e}")

    # Check skills have frontmatter
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
                            plugin_errors.append(
                                f"{name}/skills/{skill_name}: SKILL.md missing frontmatter"
                            )
                        if len(content.strip()) < 50:
                            plugin_errors.append(
                                f"{name}/skills/{skill_name}: SKILL.md too short"
                            )
                    except FileNotFoundError:
                        pass
                    except Exception as e:
                        plugin_errors.append(
                            f"{name}/skills/{skill_name}: Failed to read SKILL.md: {e}"
                        )
    except (FileNotFoundError, NotADirectoryError):
        pass

    return plugin_errors


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

        # Optimization: Use ThreadPoolExecutor to address the N+1 I/O pattern by parallelizing plugin validation.
        # This significantly improves performance when scaling to a large number of plugins.
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_plugin = {executor.submit(validate_plugin, p): p for p in plugins}
            for future in concurrent.futures.as_completed(future_to_plugin):
                try:
                    plugin_errors = future.result()
                    errors.extend(plugin_errors)
                except Exception as exc:
                    plugin = future_to_plugin[future]
                    name = plugin.get("name", "Unknown")
                    errors.append(
                        f"Plugin {name}: Unexpected error during validation: {exc}"
                    )

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

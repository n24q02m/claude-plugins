#!/usr/bin/env python3
"""Validate marketplace.json structure and plugin integrity."""

import json
import os
import re
import sys

# Pre-compile regex at module level to avoid cache lookup overhead in loops
PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")


def sanitize_log(msg: str) -> str:
    """Sanitize strings for GitHub Actions log commands."""
    return str(msg).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


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

        for plugin in plugins:
            name = plugin.get("name", "Unknown")
            if not PLUGIN_NAME_PATTERN.fullmatch(name):
                errors.append(f"Plugin {name}: invalid name format (must match ^[a-zA-Z0-9-]+$)")
                continue

            source = plugin.get("source")
            if not source:
                errors.append(f"Plugin {name}: missing source")
                continue

            # Security check: prevent path traversal
            norm_source = os.path.normpath(source)
            if os.path.isabs(norm_source) or norm_source.startswith(".."):
                errors.append(f"Plugin {name}: invalid source path (path traversal blocked)")
                continue

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
                        errors.append(f"{name}: plugin.json missing {req}")
            except FileNotFoundError:
                errors.append(f"{name}: missing {pjson}")
                continue
            except Exception as e:
                errors.append(f"{name}: Failed to parse {pjson}: {e}")

            # Check gemini-extension.json has version (optional file)
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
                                    content = f.read()
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
                                errors.append(f"{name}/skills/{skill_name}: Failed to read SKILL.md: {e}")
            except (FileNotFoundError, NotADirectoryError):
                pass

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

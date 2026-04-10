#!/usr/bin/env python3
"""Validate marketplace.json structure and plugin integrity."""

import json
import os
import re
import sys

# Pre-compile regex for performance
PLUGIN_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


def validate_marketplace():
    """Validate marketplace.json and all referenced plugins."""
    errors = []

    try:
        with open(".claude-plugin/marketplace.json") as f:
            marketplace = json.load(f)
    except Exception as e:
        print(f"::error ::Failed to load marketplace.json: {e}")
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
            if not PLUGIN_NAME_REGEX.match(name):
                errors.append(f"Plugin {name}: invalid name format (must match ^[a-zA-Z0-9_-]+$)")
                continue

            source = plugin.get("source")
            if not source:
                errors.append(f"Plugin {name}: missing source")
                continue

            plugin_dir = source.lstrip("./")

            # Check plugin.json exists and is valid
            pjson = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
            if not os.path.exists(pjson):
                errors.append(f"{name}: missing {pjson}")
                continue

            try:
                with open(pjson) as f:
                    pdata = json.load(f)
                for req in ["name", "description", "mcpServers"]:
                    if req not in pdata:
                        errors.append(f"{name}: plugin.json missing {req}")
            except Exception as e:
                errors.append(f"{name}: Failed to parse {pjson}: {e}")

            # Check gemini-extension.json has version (optional file)
            gext = os.path.join(plugin_dir, "gemini-extension.json")
            if os.path.exists(gext):
                try:
                    with open(gext) as f:
                        gdata = json.load(f)
                    if "version" not in gdata:
                        errors.append(f"{name}: gemini-extension.json missing version")
                except Exception as e:
                    errors.append(f"{name}: Failed to parse {gext}: {e}")

            # Check skills have frontmatter
            skills_dir = os.path.join(plugin_dir, "skills")
            if os.path.isdir(skills_dir):
                with os.scandir(skills_dir) as entries:
                    for entry in entries:
                        if entry.is_dir():
                            skill_name = entry.name
                            skill_file = os.path.join(entry.path, "SKILL.md")
                            if os.path.exists(skill_file):
                                try:
                                    with open(skill_file) as f:
                                        content = f.read()
                                    if not content.startswith("---"):
                                        errors.append(
                                            f"{name}/skills/{skill_name}: SKILL.md missing frontmatter"
                                        )
                                    if len(content.strip()) < 50:
                                        errors.append(
                                            f"{name}/skills/{skill_name}: SKILL.md too short"
                                        )
                                except Exception as e:
                                    errors.append(f"{name}/skills/{skill_name}: Failed to read SKILL.md: {e}")

    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"::error ::{e}")
        sys.exit(1)
    else:
        num_plugins = len(marketplace.get("plugins", []))
        print(f"All {num_plugins} plugins validated successfully")


if __name__ == "__main__":
    validate_marketplace()

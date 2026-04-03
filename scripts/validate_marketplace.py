#!/usr/bin/env python3
"""Validate marketplace.json structure and plugin integrity."""

import json
import os
import sys


def validate_marketplace():
    """Validate marketplace.json and all referenced plugins."""
    with open(".claude-plugin/marketplace.json") as f:
        marketplace = json.load(f)

    errors = []
    required = ["name", "metadata", "owner", "plugins"]
    for field in required:
        if field not in marketplace:
            errors.append(f"Missing top-level field: {field}")

    if "plugins" in marketplace:
        plugins = marketplace["plugins"]
        if not plugins:
            errors.append("No plugins defined in marketplace.json")

        for plugin in plugins:
            name = plugin.get("name", "Unknown")
            source = plugin.get("source")
            if not source:
                errors.append(f"{name}: missing source field")
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
                errors.append(f"{name}: failed to parse {pjson}: {e}")

            # gemini-extension.json is optional
            gext = os.path.join(plugin_dir, "gemini-extension.json")
            if os.path.exists(gext):
                try:
                    with open(gext) as f:
                        gdata = json.load(f)
                    if "version" not in gdata:
                        errors.append(f"{name}: gemini-extension.json missing version")
                except Exception as e:
                    errors.append(f"{name}: failed to parse {gext}: {e}")

            # Check skills have frontmatter
            skills_dir = os.path.join(plugin_dir, "skills")
            if os.path.isdir(skills_dir):
                for skill_name in os.listdir(skills_dir):
                    skill_file = os.path.join(skills_dir, skill_name, "SKILL.md")
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
                            errors.append(f"{name}/skills/{skill_name}: failed to read SKILL.md: {e}")

    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"All {len(marketplace.get('plugins', []))} plugins validated successfully")


if __name__ == "__main__":
    validate_marketplace()

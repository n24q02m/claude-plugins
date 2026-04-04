"""Validate marketplace.json structure and plugin integrity."""

import json
import os
import sys


def validate_marketplace():
    """Validate marketplace.json and all referenced plugins."""
    with open(".claude-plugin/marketplace.json") as f:
        marketplace = json.load(f)

    required = ["name", "metadata", "owner", "plugins"]
    for field in required:
        assert field in marketplace, f"Missing field: {field}"

    plugins = marketplace["plugins"]
    assert len(plugins) > 0, "No plugins defined"

    errors = []
    for plugin in plugins:
        name = plugin["name"]
        source = plugin["source"]
        plugin_dir = source.lstrip("./")

        # Check plugin.json exists and is valid
        pjson = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
        if not os.path.exists(pjson):
            errors.append(f"{name}: missing {pjson}")
            continue
        with open(pjson) as f:
            pdata = json.load(f)
        for req in ["name", "description", "mcpServers"]:
            if req not in pdata:
                errors.append(f"{name}: plugin.json missing {req}")

        # Check gemini-extension.json has version (optional file)
        gext = os.path.join(plugin_dir, "gemini-extension.json")
        if os.path.exists(gext):
            with open(gext) as f:
                gdata = json.load(f)
            if "version" not in gdata:
                errors.append(f"{name}: gemini-extension.json missing version")

        # Check skills have frontmatter
        skills_dir = os.path.join(plugin_dir, "skills")
        if os.path.isdir(skills_dir):
            for skill_name in os.listdir(skills_dir):
                skill_file = os.path.join(skills_dir, skill_name, "SKILL.md")
                if os.path.exists(skill_file):
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

    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"All {len(plugins)} plugins validated successfully")


if __name__ == "__main__":
    validate_marketplace()

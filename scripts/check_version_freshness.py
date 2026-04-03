"""Check marketplace plugin versions against latest GitHub releases."""

import json
import os
import subprocess
import sys


def check_version_freshness():
    """Compare marketplace versions with latest stable releases."""
    with open(".claude-plugin/marketplace.json") as f:
        marketplace = json.load(f)

    stale = []
    for plugin in marketplace["plugins"]:
        name = plugin["name"]
        source = plugin["source"].lstrip("./")

        # Get marketplace version (try gemini-extension.json then plugin.json)
        marketplace_ver = "unknown"
        gext_path = f"{source}/gemini-extension.json"
        pjson_path = f"{source}/.claude-plugin/plugin.json"

        if os.path.exists(gext_path):
            try:
                with open(gext_path) as f:
                    marketplace_ver = json.load(f).get("version", "unknown")
            except Exception:
                pass
        elif os.path.exists(pjson_path):
            try:
                with open(pjson_path) as f:
                    marketplace_ver = json.load(f).get("version", "unknown")
            except Exception:
                pass

        # Get latest stable release from source repo
        result = subprocess.run(
            [
                "gh",
                "release",
                "view",
                "--repo",
                f"n24q02m/{name}",
                "--json",
                "tagName",
                "-q",
                ".tagName",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            latest_tag = result.stdout.strip().lstrip("v")
            if marketplace_ver != latest_tag:
                stale.append(
                    f"{name}: marketplace={marketplace_ver}, latest={latest_tag}"
                )
                print(
                    f"::warning ::{name} is stale: marketplace={marketplace_ver}, latest={latest_tag}"
                )
            else:
                print(f"{name}: up-to-date ({marketplace_ver})")
        else:
            print(f"{name}: no release found (marketplace={marketplace_ver})")

    if stale:
        print(f"\n{len(stale)} plugin(s) need sync")
    else:
        print("\nAll plugins up-to-date")


if __name__ == "__main__":
    check_version_freshness()

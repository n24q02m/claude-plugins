#!/usr/bin/env python3
"""Check marketplace plugin versions against latest GitHub releases."""

import json
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
        gext_path = f"{source}/gemini-extension.json"

        # Get marketplace version
        try:
            with open(gext_path) as f:
                gdata = json.load(f)
            marketplace_ver = gdata.get("version", "unknown")
        except Exception:
            marketplace_ver = "missing"

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

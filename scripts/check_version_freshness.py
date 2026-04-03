"""Check marketplace plugin versions against latest GitHub releases."""

import json
import os
import subprocess
import sys


def check_version_freshness():
    """Compare marketplace versions with latest stable releases."""
    marketplace_path = ".claude-plugin/marketplace.json"
    if not os.path.exists(marketplace_path):
        print(f"Error: {marketplace_path} not found", file=sys.stderr)
        sys.exit(1)

    with open(marketplace_path) as f:
        marketplace = json.load(f)

    owner = marketplace.get("owner", {}).get("name", "n24q02m")
    plugins = marketplace.get("plugins", [])

    if not plugins:
        print("No plugins found in marketplace.json")
        return

    stale = []
    for plugin in plugins:
        name = plugin.get("name")
        source = plugin.get("source", "").lstrip("./")
        if not name or not source:
            continue

        pjson_path = os.path.join(source, ".claude-plugin", "plugin.json")

        # Get marketplace version from plugin.json
        try:
            with open(pjson_path) as f:
                pdata = json.load(f)
            marketplace_ver = pdata.get("version", "unknown")
        except Exception:
            marketplace_ver = "missing"

        # Get latest stable release from source repo
        try:
            result = subprocess.run(
                [
                    "gh",
                    "release",
                    "view",
                    "--repo",
                    f"{owner}/{name}",
                    "--json",
                    "tagName",
                    "-q",
                    ".tagName",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                latest_tag = result.stdout.strip().lstrip("v")
                if marketplace_ver != latest_tag:
                    stale.append(
                        f"{name}: marketplace={marketplace_ver}, latest={latest_tag}"
                    )
                    print(
                        f"::error ::{name} is stale: marketplace={marketplace_ver}, latest={latest_tag}"
                    )
                else:
                    print(f"{name}: up-to-date ({marketplace_ver})")
            else:
                print(f"{name}: no release found or error (marketplace={marketplace_ver})")
        except subprocess.TimeoutExpired:
            print(f"{name}: timeout while checking latest release", file=sys.stderr)
        except Exception as e:
            print(f"Error checking {name}: {e}", file=sys.stderr)

    if stale:
        print(f"\n{len(stale)} plugin(s) need sync")
        sys.exit(1)
    else:
        print("\nAll plugins up-to-date")
        sys.exit(0)


if __name__ == "__main__":
    check_version_freshness()

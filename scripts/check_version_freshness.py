"""Check marketplace plugin versions against latest GitHub releases."""

import concurrent.futures
import json
import os
import subprocess
import sys


def check_plugin(plugin):
    """Check a single plugin's version against its latest GitHub release."""
    name = plugin["name"]
    source = plugin["source"].lstrip("./")

    plugin_json_path = os.path.join(source, ".claude-plugin", "plugin.json")
    gext_path = os.path.join(source, "gemini-extension.json")

    # Get marketplace version: prioritize plugin.json, then gemini-extension.json
    marketplace_ver = "missing"

    if os.path.exists(plugin_json_path):
        try:
            with open(plugin_json_path) as f:
                data = json.load(f)
            marketplace_ver = data.get("version", "missing")
        except (json.JSONDecodeError, OSError):
            pass

    if marketplace_ver == "missing" and os.path.exists(gext_path):
        try:
            with open(gext_path) as f:
                data = json.load(f)
            marketplace_ver = data.get("version", "missing")
        except (json.JSONDecodeError, OSError):
            pass

    # Get latest stable release from source repo
    try:
        # Check if gh CLI is available
        subprocess.run(["gh", "--version"], capture_output=True, check=True)

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
            timeout=30,
        )
        if result.returncode == 0:
            latest_tag = result.stdout.strip().lstrip("v")
            if marketplace_ver != latest_tag:
                return {
                    "status": "stale",
                    "name": name,
                    "marketplace_ver": marketplace_ver,
                    "latest_tag": latest_tag,
                }
            else:
                return {
                    "status": "up-to-date",
                    "name": name,
                    "marketplace_ver": marketplace_ver,
                }
        else:
            return {
                "status": "no-release",
                "name": name,
                "marketplace_ver": marketplace_ver,
            }
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
        # We don't want to fail the whole script if GH is unavailable locally (e.g. during dev)
        # but in CI it should be available.
        return {
            "status": "error",
            "name": name,
            "marketplace_ver": marketplace_ver,
        }


def check_version_freshness():
    """Compare marketplace versions with latest stable releases concurrently."""
    marketplace_path = os.path.join(".claude-plugin", "marketplace.json")
    if not os.path.exists(marketplace_path):
        print(f"::error ::Marketplace file not found at {marketplace_path}")
        sys.exit(1)

    with open(marketplace_path) as f:
        marketplace = json.load(f)

    stale = []
    errors = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(check_plugin, p): p for p in marketplace["plugins"]
        }
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            name = res["name"]
            status = res["status"]
            marketplace_ver = res["marketplace_ver"]

            if status == "stale":
                latest_tag = res["latest_tag"]
                stale.append(
                    f"{name}: marketplace={marketplace_ver}, latest={latest_tag}"
                )
                print(
                    f"::warning ::{name} is stale: marketplace={marketplace_ver}, latest={latest_tag}"
                )
            elif status == "up-to-date":
                print(f"{name}: up-to-date ({marketplace_ver})")
            elif status == "no-release":
                print(f"{name}: no release found (marketplace={marketplace_ver})")
            elif status == "error":
                errors.append(name)
                # In CI, missing gh is an error. Locally it is just a warning.
                is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
                level = "error" if is_ci else "warning"
                print(
                    f"::{level} ::{name} could not be checked for latest release (marketplace={marketplace_ver})"
                )

    if stale:
        print(f"\n{len(stale)} plugin(s) need sync")
    elif errors:
        print(f"\nCompleted with {len(errors)} plugins skipped due to errors (e.g. missing 'gh' CLI)")
    else:
        print("\nAll plugins up-to-date")


if __name__ == "__main__":
    check_version_freshness()

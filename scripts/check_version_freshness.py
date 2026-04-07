"""Check marketplace plugin versions against latest GitHub releases."""

import concurrent.futures
import json
import os
import subprocess
import sys


def get_marketplace_version(plugin_dir):
    """Get version from plugin.json (priority) or gemini-extension.json."""
    # Try .claude-plugin/plugin.json first
    pjson_path = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    if os.path.exists(pjson_path):
        try:
            with open(pjson_path) as f:
                data = json.load(f)
            return data.get("version")
        except Exception:
            pass

    # Fallback to gemini-extension.json
    gext_path = os.path.join(plugin_dir, "gemini-extension.json")
    if os.path.exists(gext_path):
        try:
            with open(gext_path) as f:
                data = json.load(f)
            return data.get("version")
        except Exception:
            pass

    return None


def check_plugin(plugin):
    """Check a single plugin's version against its latest GitHub release."""
    name = plugin["name"]
    source = plugin.get("source", f"plugins/{name}").lstrip("./")

    marketplace_ver = get_marketplace_version(source) or "unknown"

    # Get latest stable release from source repo
    try:
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
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "name": name,
            "marketplace_ver": marketplace_ver,
        }
    except Exception as e:
        return {
            "status": "error",
            "name": name,
            "message": str(e),
            "marketplace_ver": marketplace_ver,
        }


def check_version_freshness():
    """Compare marketplace versions with latest stable releases concurrently."""
    marketplace_path = os.path.join(".claude-plugin", "marketplace.json")
    if not os.path.exists(marketplace_path):
        print(f"::error ::Marketplace file not found: {marketplace_path}")
        sys.exit(1)

    try:
        with open(marketplace_path) as f:
            marketplace = json.load(f)
    except Exception as e:
        print(f"::error ::Failed to parse {marketplace_path}: {e}")
        sys.exit(1)

    stale = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(check_plugin, p): p for p in marketplace.get("plugins", [])
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
            elif status == "timeout":
                print(
                    f"::error ::{name} timed out checking release (marketplace={marketplace_ver})"
                )
            elif status == "error":
                print(
                    f"::error ::{name} error: {res['message']} (marketplace={marketplace_ver})"
                )

    if stale:
        print(f"\n{len(stale)} plugin(s) need sync")
    else:
        print("\nAll plugins up-to-date")


if __name__ == "__main__":
    check_version_freshness()

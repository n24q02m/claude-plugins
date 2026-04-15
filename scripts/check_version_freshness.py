#!/usr/bin/env python3
"""Check marketplace plugin versions against latest GitHub releases."""

import concurrent.futures
import json
import subprocess
import os
import re

# Pre-compile regex at module level to avoid internal re cache lookup overhead in tight loops
NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")

def check_plugin(plugin):
    """Check a single plugin's version against its latest GitHub release."""
    name = plugin["name"]
    if not NAME_PATTERN.fullmatch(name):
        return {
            "status": "error",
            "name": name,
            "marketplace_ver": "unknown",
            "error": "invalid name format"
        }
    source = plugin["source"].lstrip("./")

    # Priority: .claude-plugin/plugin.json, fallback: gemini-extension.json
    # Optimize: Use EAFP to avoid duplicate system stat calls from os.path.exists followed by open
    pjson_path = os.path.join(source, ".claude-plugin", "plugin.json")
    gext_path = os.path.join(source, "gemini-extension.json")

    marketplace_ver = "unknown"
    try:
        with open(pjson_path) as f:
            pdata = json.load(f)
        marketplace_ver = pdata.get("version", "unknown")
    except FileNotFoundError:
        try:
            with open(gext_path) as f:
                gdata = json.load(f)
            marketplace_ver = gdata.get("version", "unknown")
        except Exception:
            pass
    except Exception:
        pass

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
            "marketplace_ver": marketplace_ver,
            "error": str(e)
        }


def check_version_freshness():
    """Compare marketplace versions with latest stable releases concurrently."""
    try:
        with open(".claude-plugin/marketplace.json") as f:
            marketplace = json.load(f)
    except Exception as e:
        print(f"::error ::Failed to load marketplace.json: {e}")
        return

    stale = []

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
            elif status == "timeout":
                print(
                    f"::error ::{name} timed out checking release (marketplace={marketplace_ver})"
                )
            elif status == "error":
                print(
                    f"::error ::{name} error: {res['error']}"
                )

    if stale:
        print(f"\n{len(stale)} plugin(s) need sync")
    else:
        print("\nAll plugins up-to-date")


if __name__ == "__main__":
    check_version_freshness()

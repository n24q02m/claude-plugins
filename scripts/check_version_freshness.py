#!/usr/bin/env python3
"""Check marketplace plugin versions against latest GitHub releases."""

import concurrent.futures
import json
import os
import re
import urllib.request
import urllib.error
import threading

# In-memory cache for API responses to avoid redundant calls
_cache = {}
_cache_lock = threading.Lock()


def get_latest_tag_api(repo):
    """Fetch the latest stable release tag from GitHub API."""
    with _cache_lock:
        if repo in _cache:
            return _cache[repo]

    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Marketplace-Version-Checker"
    }

    # Support both GITHUB_TOKEN and GH_TOKEN for authenticated requests
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            # GitHub REST API returns snake_case tag_name (gh CLI returns camelCase).
            tag = data.get("tag_name", "").lstrip("v")
            result = ("ok", tag)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            result = ("no-release", None)
        else:
            result = ("error", str(e))
    except urllib.error.URLError as e:
        if isinstance(e.reason, TimeoutError):
            result = ("timeout", None)
        else:
            result = ("error", str(e))
    except Exception as e:
        result = ("error", str(e))

    with _cache_lock:
        _cache[repo] = result
    return result

# Pre-compile regex at module level to avoid cache lookup overhead in concurrent loops
PLUGIN_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")


def check_plugin(plugin):
    """Check a single plugin's version against its latest GitHub release."""
    name = plugin["name"]
    if not PLUGIN_NAME_PATTERN.fullmatch(name):
        return {
            "status": "error",
            "name": name,
            "marketplace_ver": "unknown",
            "error": "invalid name format"
        }

    source = plugin["source"]
    norm_source = os.path.normpath(source)
    if os.path.isabs(norm_source) or norm_source.startswith(".."):
        return {
            "status": "error",
            "name": name,
            "marketplace_ver": "unknown",
            "error": "invalid source path"
        }

    source = norm_source

    # Priority: .claude-plugin/plugin.json, fallback: gemini-extension.json
    pjson_path = os.path.join(source, ".claude-plugin", "plugin.json")
    gext_path = os.path.join(source, "gemini-extension.json")

    marketplace_ver = "unknown"
    if os.path.exists(pjson_path):
        try:
            with open(pjson_path) as f:
                pdata = json.load(f)
            marketplace_ver = pdata.get("version", "unknown")
        except (OSError, json.JSONDecodeError) as e:
            print(f"::warning ::Failed to parse {pjson_path}: {e}")
    elif os.path.exists(gext_path):
        try:
            with open(gext_path) as f:
                gdata = json.load(f)
            marketplace_ver = gdata.get("version", "unknown")
        except (OSError, json.JSONDecodeError) as e:
            print(f"::warning ::Failed to parse {gext_path}: {e}")

    # Get latest stable release from source repo via API
    status, latest_tag = get_latest_tag_api(f"n24q02m/{name}")

    if status == "ok":
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
    elif status == "no-release":
        return {
            "status": "no-release",
            "name": name,
            "marketplace_ver": marketplace_ver,
        }
    elif status == "timeout":
        return {
            "status": "timeout",
            "name": name,
            "marketplace_ver": marketplace_ver,
        }
    else:
        return {
            "status": "error",
            "name": name,
            "marketplace_ver": marketplace_ver,
            "error": latest_tag # status is "error", latest_tag contains the error message
        }


def check_version_freshness():
    """Compare marketplace versions with latest stable releases concurrently."""
    try:
        with open(".claude-plugin/marketplace.json") as f:
            marketplace = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
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

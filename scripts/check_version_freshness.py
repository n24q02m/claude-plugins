#!/usr/bin/env python3
"""Check marketplace plugin versions against latest GitHub releases."""

import concurrent.futures
import json
import os
import urllib.request
import urllib.error
import urllib.parse
import functools

from utils import sanitize_log, PLUGIN_NAME_PATTERN, get_safe_path


class NoAuthRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that strips the Authorization header on cross-origin redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        m = super().redirect_request(req, fp, code, msg, headers, newurl)
        if m is not None:
            old_url_parsed = urllib.parse.urlparse(req.full_url)
            new_url_parsed = urllib.parse.urlparse(newurl)
            old_host = old_url_parsed.hostname
            new_host = new_url_parsed.hostname
            old_scheme = old_url_parsed.scheme
            new_scheme = new_url_parsed.scheme

            # Check if the hostname has changed or if there's an HTTPS to HTTP downgrade
            if old_host != new_host or (old_scheme == "https" and new_scheme == "http"):
                # Strip Authorization header to prevent token leakage (SSRF mitigation)
                for header in ["Authorization", "Cookie", "authorization", "cookie"]:
                    if m.has_header(header):
                        m.remove_header(header)
                    keys_to_remove = [
                        k for k in m.unredirected_hdrs if k.lower() == header.lower()
                    ]
                    for k in keys_to_remove:
                        del m.unredirected_hdrs[k]
        return m


_opener = urllib.request.build_opener(NoAuthRedirectHandler)

# In-memory cache for API responses to avoid redundant calls


@functools.lru_cache(maxsize=None)
def get_latest_tag_api(repo):
    """Fetch the latest stable release tag from GitHub API."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Marketplace-Version-Checker",
    }

    # Support both GITHUB_TOKEN and GH_TOKEN for authenticated requests
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with _opener.open(req, timeout=30) as response:
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

    return result


def check_plugin(plugin):
    """Check a single plugin's version against its latest GitHub release."""
    name = plugin.get("name")
    if not isinstance(name, str) or not PLUGIN_NAME_PATTERN.fullmatch(name):
        return {
            "status": "error",
            "name": name if isinstance(name, str) else "unknown",
            "marketplace_ver": "unknown",
            "error": "invalid name format",
        }

    source = plugin.get("source")
    if not isinstance(source, str):
        return {
            "status": "error",
            "name": name,
            "marketplace_ver": "unknown",
            "error": "invalid source type",
        }
    # Robust path validation: resolve symlinks and ensure path is within project root
    try:
        source = get_safe_path(os.getcwd(), source)
    except (OSError, ValueError):
        return {
            "status": "error",
            "name": name,
            "marketplace_ver": "unknown",
            "error": "invalid source path",
        }

    # Priority: .claude-plugin/plugin.json, fallback: gemini-extension.json
    pjson_path = os.path.join(source, ".claude-plugin", "plugin.json")
    gext_path = os.path.join(source, "gemini-extension.json")

    marketplace_ver = "unknown"
    # Optimization: Use EAFP to avoid redundant os.path.exists stat syscalls before open
    try:
        with open(pjson_path) as f:
            pdata = json.load(f)
        marketplace_ver = pdata.get("version", "unknown")
    except FileNotFoundError:
        try:
            with open(gext_path) as f:
                gdata = json.load(f)
            marketplace_ver = gdata.get("version", "unknown")
        except FileNotFoundError:
            pass
        except (OSError, json.JSONDecodeError) as e:
            print(f"::warning ::{sanitize_log(f'Failed to parse {gext_path}: {e}')}")
    except (OSError, json.JSONDecodeError) as e:
        print(f"::warning ::{sanitize_log(f'Failed to parse {pjson_path}: {e}')}")

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
            "error": latest_tag,  # status is "error", latest_tag contains the error message
        }


def check_version_freshness():
    """Compare marketplace versions with latest stable releases concurrently."""
    try:
        with open(".claude-plugin/marketplace.json") as f:
            marketplace = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"::error ::{sanitize_log(f'Failed to load marketplace.json: {e}')}")
        return

    stale = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_plugin, p): p for p in marketplace["plugins"]}
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
                    f"::warning ::{sanitize_log(f'{name} is stale: marketplace={marketplace_ver}, latest={latest_tag}')}"
                )
            elif status == "up-to-date":
                print(sanitize_log(f"{name}: up-to-date ({marketplace_ver})"))
            elif status == "no-release":
                print(
                    sanitize_log(
                        f"{name}: no release found (marketplace={marketplace_ver})"
                    )
                )
            elif status == "timeout":
                print(
                    f"::error ::{sanitize_log(f'{name} timed out checking release (marketplace={marketplace_ver})')}"
                )
            elif status == "error":
                print("::error ::" + sanitize_log(f"{name} error: {res['error']}"))

    if stale:
        print(f"\n{len(stale)} plugin(s) need sync")
    else:
        print("\nAll plugins up-to-date")


if __name__ == "__main__":
    check_version_freshness()

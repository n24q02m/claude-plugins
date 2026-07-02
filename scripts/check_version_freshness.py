#!/usr/bin/env python3
"""Check marketplace plugin versions against latest GitHub releases."""

import concurrent.futures
import json
import os
import urllib.request
import urllib.error
import urllib.parse

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
                headers_to_remove = ("authorization", "cookie")
                for k in [k for k in m.headers if k.lower() in headers_to_remove]:
                    del m.headers[k]
                for k in [
                    k for k in m.unredirected_hdrs if k.lower() in headers_to_remove
                ]:
                    del m.unredirected_hdrs[k]
        return m


_opener = urllib.request.build_opener(NoAuthRedirectHandler)


# In-memory cache for API responses to avoid redundant calls
_latest_tag_cache = {}


def get_latest_tag_api(repo):
    """Fetch the latest stable release tag from GitHub API."""
    if repo in _latest_tag_cache:
        return _latest_tag_cache[repo]

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

    _latest_tag_cache[repo] = result
    return result


def _fetch_latest_tags_graphql(owner, repo_names):
    """Fetch latest release tags for multiple repos in a single GraphQL call."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return

    # Filter out repos already in cache
    repos_to_fetch = [r for r in repo_names if f"{owner}/{r}" not in _latest_tag_cache]
    if not repos_to_fetch:
        return

    # Build aliases for GraphQL (must start with letter and be alphanumeric)
    def to_alias(name):
        return "repo_" + name.replace("-", "_")

    # Construct the GraphQL query using parameterized variables
    query_parts = []
    variables = {"owner": owner}
    var_defs_list = ["$owner: String!"]

    for i, repo in enumerate(repos_to_fetch):
        alias = to_alias(repo)
        repo_var = f"repo{i}"
        variables[repo_var] = repo
        var_defs_list.append(f"${repo_var}: String!")
        query_parts.append(
            f"{alias}: repository(owner: $owner, name: ${repo_var}) {{ "
            "latestRelease { tagName } }"
        )

    var_defs = ", ".join(var_defs_list)
    query = f"query({var_defs}) {{ " + " ".join(query_parts) + " }"
    url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"token {token}",
        "Content-Type": "application/json",
        "User-Agent": "Marketplace-Version-Checker",
    }
    data = json.dumps({"query": query, "variables": variables}).encode()

    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with _opener.open(req, timeout=30) as response:
            result_data = json.loads(response.read().decode())
            if "data" in result_data:
                for repo in repos_to_fetch:
                    alias = to_alias(repo)
                    repo_data = result_data["data"].get(alias)
                    full_repo = f"{owner}/{repo}"
                    if repo_data and repo_data.get("latestRelease"):
                        tag = repo_data["latestRelease"]["tagName"].lstrip("v")
                        _latest_tag_cache[full_repo] = ("ok", tag)
                    elif repo_data:
                        _latest_tag_cache[full_repo] = ("no-release", None)
    except Exception as e:
        # Silently fall back to REST if GraphQL fails
        print(f"::debug ::GraphQL batch fetch failed: {e}")


def _get_marketplace_version(source):
    """Retrieve the plugin version from its manifest file (plugin.json or gemini-extension.json)."""
    pjson_path = os.path.join(source, ".claude-plugin", "plugin.json")
    gext_path = os.path.join(source, "gemini-extension.json")

    # Priority: .claude-plugin/plugin.json, fallback: gemini-extension.json
    try:
        with open(pjson_path) as f:
            pdata = json.load(f)
        return pdata.get("version", "unknown")
    except FileNotFoundError:
        try:
            with open(gext_path) as f:
                gdata = json.load(f)
            return gdata.get("version", "unknown")
        except FileNotFoundError:
            return "unknown"
        except (OSError, json.JSONDecodeError) as e:
            print(f"::warning ::{sanitize_log(f'Failed to parse {gext_path}: {e}')}")
            return "unknown"
    except (OSError, json.JSONDecodeError) as e:
        print(f"::warning ::{sanitize_log(f'Failed to parse {pjson_path}: {e}')}")
        return "unknown"


def check_plugin(plugin, owner):
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

    marketplace_ver = _get_marketplace_version(source)

    # Get latest stable release from source repo via API
    status, latest_tag = get_latest_tag_api(f"{owner}/{name}")

    result = {"name": name, "marketplace_ver": marketplace_ver, "status": status}

    if status == "ok":
        if marketplace_ver != latest_tag:
            result.update({"status": "stale", "latest_tag": latest_tag})
        else:
            result["status"] = "up-to-date"
    elif status == "error":
        result["error"] = latest_tag

    return result


def check_version_freshness():
    """Compare marketplace versions with latest stable releases concurrently."""
    try:
        with open(".claude-plugin/marketplace.json") as f:
            marketplace = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"::error ::{sanitize_log(f'Failed to load marketplace.json: {e}')}")
        return

    owner = marketplace.get("owner", {}).get("name", "n24q02m")
    plugin_names = [
        p.get("name") for p in marketplace.get("plugins", []) if p.get("name")
    ]

    # Pre-populate cache using GraphQL batch fetch if possible
    _fetch_latest_tags_graphql(owner, plugin_names)

    stale = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(check_plugin, p, owner): p for p in marketplace["plugins"]
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

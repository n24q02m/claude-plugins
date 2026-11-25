#!/usr/bin/env python3
"""Generate per-IDE MCP client manifests and portable adapter rows.

Reads ``.claude-plugin/marketplace.json`` and each plugin's
``.claude-plugin/plugin.json`` using Python stdlib only, writing:

- ``manifests/claude-code.json``
- ``manifests/cursor.json``
- ``manifests/windsurf.json``
- ``manifests/vscode.json``
- ``manifests/gemini-cli.json``
- ``manifests/opencode.json``
- ``manifests/codex.toml``
- ``manifests/harness-adapters.json``

Run with ``--check`` in CI to fail if any generated file is missing or drifted.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
DEFAULT_OUTPUT_DIR = ROOT / "manifests"

_USER_CONFIG_RE = re.compile(r"\$\{user_config\.([A-Za-z0-9_]+)\}")
_ADAPTER_HARNESSES = (
    "claude-code",
    "codex-cli",
    "opencode",
    "cursor",
    "github-copilot-vscode",
    "gemini-cli",
)


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_array(values: list[str]) -> str:
    return "[" + ", ".join(_toml_quote(item) for item in values) + "]"


def _substitute_var(raw: str, user_config: dict, *, template: str, use_default: bool = True) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if use_default:
            default = user_config.get(key, {}).get("default")
            if isinstance(default, str) and default:
                return default
        return template.format(key=key.upper())

    return _USER_CONFIG_RE.sub(_replace, raw)


def _extract_user_vars(env_map: dict[str, str]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for name, raw in sorted(env_map.items()):
        match = _USER_CONFIG_RE.search(raw)
        if match:
            items.append({"name": match.group(1).upper(), "source": "user-config"})
        else:
            items.append({"name": name.upper(), "source": "environment"})
    return items


def _load_plugins(marketplace_path: Path) -> list[dict]:
    marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    base_dir = marketplace_path.resolve().parents[1]
    plugins: list[dict] = []
    for entry in marketplace["plugins"]:
        source_rel = entry["source"].removeprefix("./")
        pjson_path = base_dir / source_rel / ".claude-plugin" / "plugin.json"
        pdata = json.loads(pjson_path.read_text(encoding="utf-8"))
        plugins.append(
            {
                "name": entry["name"],
                "source_ref": source_rel,
                "manifest": pdata,
            }
        )
    return plugins


def _stdio_entry(server: dict, user_config: dict, *, template: str) -> dict:
    entry: dict = {
        "command": server["command"],
        "args": list(server.get("args", [])),
    }
    raw_env = server.get("env") or {}
    if raw_env:
        entry["env"] = {
            k: _substitute_var(v, user_config, template=template)
            for k, v in raw_env.items()
        }
    return entry


def _http_entry(
    server: dict,
    user_config: dict,
    *,
    url_key: str,
    template: str,
    include_type: str | None = None,
) -> dict:
    url = _substitute_var(server["url"], user_config, template=template)
    entry: dict = {}
    if include_type:
        entry["type"] = include_type
    entry[url_key] = url
    headers = {
        k: _substitute_var(v, user_config, template=template, use_default=False)
        for k, v in (server.get("headers") or {}).items()
    }
    if headers:
        entry["headers"] = headers
    return entry


def _render_standard_json(plugins: list[dict], *, flavor: str) -> str:
    top_key = "servers" if flavor == "vscode" else "mcpServers"
    template = "${{env:{key}}}" if flavor == "vscode" else "${{{key}}}"
    servers: dict[str, dict] = {}
    for plugin in plugins:
        name = plugin["name"]
        pdata = plugin["manifest"]
        user_config = pdata.get("userConfig") or {}
        server = pdata["mcpServers"][name]
        if server.get("type") == "http":
            url_key = {
                "windsurf": "serverUrl",
                "gemini-cli": "httpUrl",
            }.get(flavor, "url")
            include_type = "http" if flavor in {"claude-code", "vscode"} else None
            servers[name] = _http_entry(
                server,
                user_config,
                url_key=url_key,
                template=template,
                include_type=include_type,
            )
        else:
            entry = _stdio_entry(server, user_config, template=template)
            if flavor == "vscode":
                entry = {"type": "stdio", **entry}
            servers[name] = entry
    return json.dumps({top_key: servers}, indent=2) + "\n"


def _render_opencode_json(plugins: list[dict]) -> str:
    mcp: dict[str, dict] = {}
    for plugin in plugins:
        name = plugin["name"]
        pdata = plugin["manifest"]
        user_config = pdata.get("userConfig") or {}
        server = pdata["mcpServers"][name]
        if server.get("type") == "http":
            entry = _http_entry(
                server,
                user_config,
                url_key="url",
                template="{{env:{key}}}",
                include_type="remote",
            )
            mcp[name] = entry
        else:
            item: dict = {
                "type": "local",
                "command": [server["command"], *server.get("args", [])],
            }
            raw_env = server.get("env") or {}
            if raw_env:
                item["environment"] = {
                    k: _substitute_var(v, user_config, template="{{env:{key}}}")
                    for k, v in raw_env.items()
                }
            mcp[name] = item
    payload = {"$schema": "https://opencode.ai/config.json", "mcp": mcp}
    return json.dumps(payload, indent=2) + "\n"


def _render_codex_toml(plugins: list[dict]) -> str:
    lines = ["# Generated by scripts/generate_ide_manifests.py -- do not edit manually.", ""]
    for plugin in plugins:
        name = plugin["name"]
        pdata = plugin["manifest"]
        user_config = pdata.get("userConfig") or {}
        server = pdata["mcpServers"][name]
        lines.append(f"[mcp_servers.{name}]")
        if server.get("type") == "http":
            url = _substitute_var(server["url"], user_config, template="${{{key}}}")
            lines.append(f"url = {_toml_quote(url)}")
            for hval in (server.get("headers") or {}).values():
                match = _USER_CONFIG_RE.search(hval)
                if match:
                    lines.append(f"bearer_token_env_var = {_toml_quote(match.group(1).upper())}")
                    break
        else:
            lines.append(f"command = {_toml_quote(server['command'])}")
            lines.append(f"args = {_toml_array(list(server.get('args', [])))}")
            raw_env = server.get("env") or {}
            if raw_env:
                lines.append("")
                lines.append(f"[mcp_servers.{name}.env]")
                for k, v in raw_env.items():
                    rendered = _substitute_var(v, user_config, template="${{{key}}}")
                    lines.append(f"{k} = {_toml_quote(rendered)}")
        lines.append("")
    return "\n".join(lines)


def _render_harness_adapters_json(plugins: list[dict]) -> str:
    adapters: list[dict] = []
    for plugin in plugins:
        name = plugin["name"]
        pdata = plugin["manifest"]
        server = pdata["mcpServers"][name]
        is_http = server.get("type") == "http"
        env_vars = _extract_user_vars(server.get("env") or {})
        for header_val in (server.get("headers") or {}).values():
            match = _USER_CONFIG_RE.search(header_val)
            if match:
                env_vars.append({"name": match.group(1).upper(), "source": "user-config"})
        url_match = _USER_CONFIG_RE.search(server.get("url", ""))
        if url_match:
            env_vars.append({"name": url_match.group(1).upper(), "source": "user-config"})

        seen_vars: set[tuple[str, str]] = set()
        deduped_vars: list[dict[str, str]] = []
        for item in env_vars:
            key = (item["name"], item["source"])
            if key not in seen_vars:
                seen_vars.add(key)
                deduped_vars.append(item)

        docs = [f"{plugin['source_ref']}/overview.md"]
        repo_url = pdata.get("repository")
        if isinstance(repo_url, str) and repo_url.startswith("https://"):
            docs.append(repo_url)

        for harness in _ADAPTER_HARNESSES:
            row: dict = {
                "product": {
                    "id": name,
                    "name": pdata["name"],
                    "version": pdata.get("version", "0.0.0"),
                    "source_ref": plugin["source_ref"],
                },
                "harness": harness,
                "layer": "mcp-transport",
                "transport": "streamable-http" if is_http else "stdio",
                "docs": docs,
                "verification": {
                    "capability_state": "SUPPORTED",
                    "installed_state": "UNVERIFIED",
                    "loaded_state": "UNVERIFIED",
                    "domain_verified_state": "UNVERIFIED",
                    "domain_call_evidence": {
                        "calls": [],
                        "reason": "Generated IDE adapter manifest only; runtime tool invocation was not executed.",
                    },
                },
            }
            if is_http:
                row["endpoint_ref"] = "mcp"
            else:
                row["command"] = {
                    "program": server["command"],
                    "args": list(server.get("args", [])),
                }
            if deduped_vars:
                row["env_interpolation"] = deduped_vars
            adapters.append(row)
    return json.dumps({"adapters": adapters}, indent=2) + "\n"


def render_all(marketplace_path: Path = MARKETPLACE_PATH) -> dict[str, str]:
    """Build deterministic contents for every IDE manifest target."""
    plugins = _load_plugins(marketplace_path)
    return {
        "claude-code.json": _render_standard_json(plugins, flavor="claude-code"),
        "cursor.json": _render_standard_json(plugins, flavor="cursor"),
        "windsurf.json": _render_standard_json(plugins, flavor="windsurf"),
        "vscode.json": _render_standard_json(plugins, flavor="vscode"),
        "gemini-cli.json": _render_standard_json(plugins, flavor="gemini-cli"),
        "opencode.json": _render_opencode_json(plugins),
        "codex.toml": _render_codex_toml(plugins),
        "harness-adapters.json": _render_harness_adapters_json(plugins),
    }


def sync_manifests(
    *,
    marketplace_path: Path = MARKETPLACE_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    check: bool = False,
) -> list[str]:
    """Write or verify all generated manifests; returns list of out-of-date filenames."""
    rendered = render_all(marketplace_path)
    drifted: list[str] = []
    if not check:
        output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in rendered.items():
        target = output_dir / filename
        current = target.read_text(encoding="utf-8") if target.is_file() else None
        if current != content:
            if check:
                drifted.append(filename)
            else:
                target.write_text(content, encoding="utf-8", newline="\n")
    return drifted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify manifests on disk match generated output without writing",
    )
    parser.add_argument(
        "--marketplace",
        type=Path,
        default=MARKETPLACE_PATH,
        help="path to .claude-plugin/marketplace.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="directory where generated manifests live",
    )
    args = parser.parse_args(argv)
    drifted = sync_manifests(
        marketplace_path=args.marketplace,
        output_dir=args.output_dir,
        check=args.check,
    )
    if args.check and drifted:
        print(
            "IDE manifests out of date: " + ", ".join(drifted),
            file=sys.stderr,
        )
        return 1
    if not args.check:
        print(f"Generated {len(render_all(args.marketplace))} IDE manifest files in {args.output_dir}")
    else:
        print("All IDE manifests are up to date.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

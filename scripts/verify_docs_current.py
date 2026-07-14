#!/usr/bin/env python3
"""Verify per-server docs stay current with shipped plugin manifests (WS-E / E6).

The prose docs on mcp.n24q02m.com are hand-maintained in ``plugins/<name>/*.md``
(the plugin-sync CD job copies plugin.json / skills / hooks from source repos,
never the ``.md`` files). That means a server can ship a new user-facing config
param and the docs silently fall behind. This gate closes that loop.

For every plugin that declares an ``mcpServers`` manifest, it checks:

1. Doc-set completeness -- the required prose pages exist:
   ``overview.md``, ``setup.md``, ``tools.md``, ``troubleshooting.md``.
   (Catches the "new server shipped with no docs" recurrence.)
2. Config-param coverage -- every ``userConfig`` key in ``plugin.json`` is
   mentioned in at least one of the plugin's ``.md`` files.
   (Catches "shipped a new param without a docs entry".)

The foundation library (mcp-core) has no ``mcpServers`` manifest and is skipped
by design -- it documents architecture, not an install/tool surface.

Note: tool/action-level parity (``tools/list`` output vs ``tools.md``) is NOT
checked here -- that requires running each server and so belongs in each server
repo's own CI, not in this static, self-contained marketplace check.

Exit code 0 = docs current; 1 = drift detected (prints GitHub Actions errors).
"""

import json
import os
import sys

from utils import sanitize_log

PLUGINS_DIR = "plugins"

# Prose pages every runnable server must ship for the docs site.
REQUIRED_DOCS = ("overview.md", "setup.md", "tools.md", "troubleshooting.md")


def _markdown_blob(plugin_dir: str) -> str:
    """Concatenate every top-level ``.md`` file in the plugin dir."""
    parts = []
    try:
        with os.scandir(plugin_dir) as entries:
            for entry in entries:
                if entry.is_file() and entry.name.endswith(".md"):
                    try:
                        with open(entry.path, encoding="utf-8") as f:
                            parts.append(f.read())
                    except OSError as e:
                        parts.append("")
                        print(
                            f"::warning ::{sanitize_log(f'{plugin_dir}: could not read {entry.name}: {e}')}"
                        )
    except (FileNotFoundError, NotADirectoryError):
        pass
    return "\n".join(parts)


def _verify_plugin(name: str, plugin_dir: str) -> list[str]:
    """Return a list of drift errors for a single plugin (empty = OK)."""
    errors: list[str] = []

    pjson = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    try:
        with open(pjson, encoding="utf-8") as f:
            pdata = json.load(f)
    except FileNotFoundError:
        # Not a runnable plugin (e.g. the mcp-core foundation library) -- skip.
        return errors
    except (OSError, json.JSONDecodeError) as e:
        return [f"{name}: failed to parse plugin.json: {e}"]

    # Only servers with an mcpServers manifest have an install/tool surface.
    if not pdata.get("mcpServers"):
        return errors

    # (1) Doc-set completeness.
    for doc in REQUIRED_DOCS:
        if not os.path.isfile(os.path.join(plugin_dir, doc)):
            errors.append(
                f"{name}: missing required docs page '{doc}' "
                f"(add plugins/{name}/{doc})"
            )

    # (2) Config-param coverage.
    blob = _markdown_blob(plugin_dir)
    user_config = pdata.get("userConfig") or {}
    for key in user_config:
        if key not in blob:
            errors.append(
                f"{name}: userConfig key '{key}' is shipped in plugin.json but "
                f"not documented in any plugins/{name}/*.md page"
            )

    return errors


def verify_docs_current() -> None:
    if not os.path.isdir(PLUGINS_DIR):
        print(f"::error ::{sanitize_log(f'plugins dir not found: {PLUGINS_DIR}')}")
        sys.exit(1)

    errors: list[str] = []
    checked = 0
    with os.scandir(PLUGINS_DIR) as entries:
        for entry in sorted(entries, key=lambda e: e.name):
            if not entry.is_dir():
                continue
            plugin_errors = _verify_plugin(entry.name, entry.path)
            # A plugin with an mcpServers manifest was actually verified.
            pjson = os.path.join(entry.path, ".claude-plugin", "plugin.json")
            if os.path.isfile(pjson):
                try:
                    with open(pjson, encoding="utf-8") as f:
                        if json.load(f).get("mcpServers"):
                            checked += 1
                except (OSError, json.JSONDecodeError):
                    pass
            errors.extend(plugin_errors)

    if errors:
        print("Docs currency errors (docs drifted from shipped plugin.json):")
        for e in errors:
            print(f"::error ::{sanitize_log(e)}")
        sys.exit(1)

    print(f"All {checked} server(s) have current docs (pages + config-param coverage).")


if __name__ == "__main__":
    verify_docs_current()

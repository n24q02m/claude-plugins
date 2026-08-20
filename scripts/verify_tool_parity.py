#!/usr/bin/env python3
"""Verify ``plugins/<name>/tools.md`` names the same tools the server exposes.

Why this exists
---------------
``plugins/<name>/tools.md`` is hand-written prose that lives only in this repo:
the plugin-sync job (``.github/workflows/cd.yml``) copies ``plugin.json``,
``gemini-extension.json``, ``skills/``, ``hooks/``, ``commands/`` and
``chat.py`` from each source repo, never the ``.md`` pages. ``plugin.json``
itself carries no tool list. So when a server renames a tool, nothing in this
repo notices -- the marketplace and the docs site keep showing the old name
while the running server answers to the new one.

``verify_docs_current.py`` deliberately stops short of this check (it is static
and self-contained). This script closes the gap by asking the server itself:
it launches the exact command shipped in ``plugin.json``'s ``mcpServers`` entry
over stdio, performs the MCP ``initialize`` handshake, calls ``tools/list``,
and compares that name set against the names declared in ``tools.md``.

Declared names are read from the two conventions already used across the nine
``tools.md`` pages:

1. An ``## <tool_name>`` H2 heading (wet, mnemo, notion, email, telegram, crg,
   imagine, workspace).
2. The first column of a markdown table whose header column is ``Tool``
   (godot's single overview table, mnemo's single-purpose tool table).

Headings that are prose ("Single-purpose memory tools") are ignored because
they do not look like a tool identifier.

Usage::

    python3 scripts/verify_tool_parity.py --all
    python3 scripts/verify_tool_parity.py wet-mcp mnemo-mcp
    python3 scripts/verify_tool_parity.py --declared-only --all   # no network
    python3 scripts/verify_tool_parity.py --all --jobs 2          # throttle

Plugins are checked concurrently. The default is one worker per selected
plugin -- every server is probed in a single wave, so the run costs the
slowest server rather than the sum of them. Almost none of that wait is CPU
(it is ``uvx``/``npx`` fetching a package, then blocking on the server's
stdio), so a 2-core runner is not the constraint; ``--jobs`` is kept for
throttling by hand.

Two streams, on purpose:

* stdout carries the report, printed in plugin order -- each plugin's lines
  are collected and flushed once every plugin has finished, so the report
  reads exactly as it would running one at a time.
* stderr carries a ``[parity]`` progress line as each plugin starts and
  finishes, flushed immediately. A run killed by the CI job timeout is
  otherwise silent about which server it was waiting on.

Exit code 0 = names match; 1 = drift (prints GitHub Actions error annotations).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable

from utils import sanitize_log

PLUGINS_DIR = "plugins"

# A tool identifier as used across this stack: lowercase snake_case, optionally
# with the ``__`` namespace separator (e.g. ``config__open_relay``).
TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:_{1,2}[a-z0-9]+)*$")

# plugin.json env values are templates the client fills in
# (e.g. "${user_config.GEMINI_API_KEY}"). Passing them through literally would
# hand the server a nonsense credential, so they are dropped and the server
# starts on its defaults -- tools/list does not depend on credentials.
USER_CONFIG_TEMPLATE_RE = re.compile(r"^\$\{user_config\.([^}]+)\}$")

# Five of the nine servers refuse to start in stdio mode with no credentials at
# all (notion, email, telegram, imagine, workspace) -- they print a setup notice
# and exit before any client can call tools/list. Their gate checks that a value
# is *present*, not that it works, so an obviously fake value is enough to reach
# the tool registry. Nothing is ever sent upstream: the probe stops at
# tools/list. This is only used on a second attempt, after a credential-free
# start has already failed, so servers that need no credentials never see it.
PROBE_PLACEHOLDER = "tool-parity-probe-not-a-real-credential"

DEFAULT_TIMEOUT_S = 600


class ProbeTimeout(RuntimeError):
    """The server was still alive but never answered ``tools/list``.

    Kept distinct from every other probe failure because it is the one case
    the placeholder-credential retry cannot help. That retry exists for a
    server that *refuses to start* without a credential -- it exits in
    seconds, and the second attempt is cheap. A server that hangs has not
    refused anything; it will hang identically on the retry and burn another
    full ``timeout``, which is exactly how this check outgrew its CI budget.
    """


# --------------------------------------------------------------------------
# Declared names (static, no network)
# --------------------------------------------------------------------------


def _table_row_cells(line: str) -> list[str]:
    """Split a markdown table row into trimmed cells (outer pipes dropped)."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return []
    return [c.strip() for c in stripped.strip("|").split("|")]


_UNBACKTICK_RE = re.compile(r"^`([^`]+)`")
_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
_TABLE_SEPARATOR_RE = re.compile(r":?-{2,}:?")


def _unbacktick(cell: str) -> str:
    match = _UNBACKTICK_RE.match(cell)
    return match.group(1) if match else cell


def declared_names(markdown: str) -> set[str]:
    """Extract the tool names a ``tools.md`` page declares."""
    names: set[str] = set()
    in_tool_table = False

    for line in markdown.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            in_tool_table = False
            candidate = _unbacktick(heading.group(1))
            if TOOL_NAME_RE.match(candidate):
                names.add(candidate)
            continue

        cells = _table_row_cells(line)
        if not cells:
            in_tool_table = False
            continue

        # Header row of a tool table: first column literally named "Tool".
        if cells[0].lower() == "tool":
            in_tool_table = True
            continue

        # Separator row (|---|---|) keeps the table open.
        if all(_TABLE_SEPARATOR_RE.fullmatch(c) for c in cells if c):
            continue

        if in_tool_table:
            candidate = _unbacktick(cells[0])
            if TOOL_NAME_RE.match(candidate):
                names.add(candidate)

    return names


def read_declared(plugin_dir: str) -> set[str]:
    path = os.path.join(plugin_dir, "tools.md")
    with open(path, encoding="utf-8") as f:
        return declared_names(f.read())


# --------------------------------------------------------------------------
# Live names (spawns the shipped server over stdio)
# --------------------------------------------------------------------------


def pin_version(spec: str, version: str) -> str:
    """Pin a package spec to an exact published version.

    Both ecosystems in use accept ``name@version``: uv (``wet-mcp@3.6.0``) and
    npm (``@n24q02m/better-email-mcp@1.37.0``). The leading ``@`` of an npm
    scope must survive, so only a separator ``@`` past position 0 is replaced.
    """
    at = spec.rfind("@")
    base = spec[:at] if at > 0 else spec
    return f"{base}@{version}"


def server_spec(
    plugin_dir: str, version: str | None = None, placeholders: bool = False
) -> tuple[list[str], dict[str, str]] | None:
    """Return (argv, env) for the plugin's MCP server, or None if it has none."""
    manifest = os.path.join(plugin_dir, ".claude-plugin", "plugin.json")
    with open(manifest, encoding="utf-8") as f:
        data = json.load(f)

    servers = data.get("mcpServers") or {}
    if not servers:
        return None
    if len(servers) != 1:
        raise ValueError(
            f"expected exactly one mcpServers entry, found {sorted(servers)}"
        )

    entry = next(iter(servers.values()))
    args = list(entry.get("args", []))

    if version:
        # The package spec is the last argument that is not a flag or a flag
        # value -- true for every manifest in this repo (uvx --python 3.13 PKG,
        # npx --yes PKG).
        package_indices = [i for i, a in enumerate(args) if not a.startswith("-")]
        if not package_indices:
            raise ValueError("no package argument to pin a version onto")
        last = package_indices[-1]
        args[last] = pin_version(args[last], version)

    # Resolve through PATH so Windows picks up the ``npx.cmd`` / ``uvx.exe``
    # shim; on Linux runners this is a no-op.
    command = shutil.which(entry["command"]) or entry["command"]
    argv = [command, *args]

    user_config = data.get("userConfig") or {}

    env: dict[str, str] = {}
    for key, value in (entry.get("env") or {}).items():
        template = (
            USER_CONFIG_TEMPLATE_RE.match(value) if isinstance(value, str) else None
        )
        if template:
            option = user_config.get(template.group(1)) or {}
            gates_startup = option.get("sensitive") or option.get("required")
            if placeholders and gates_startup:
                env[key] = PROBE_PLACEHOLDER
            # Otherwise leave it unset so the server starts on its defaults --
            # passing "${user_config.X}" through literally would be worse than
            # absent, and non-credential options (model chains, tuning) must not
            # be filled with junk.
            continue
        env[key] = value
    env["MCP_TRANSPORT"] = "stdio"
    return argv, env


def _default_uv_cache() -> str | None:
    """uv's cache location under the *real* profile, before HOME is redirected."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        return os.path.join(base, "uv", "cache") if base else None
    cache_home = os.environ.get("XDG_CACHE_HOME") or os.path.join(
        os.path.expanduser("~"), ".cache"
    )
    return os.path.join(cache_home, "uv")


def _default_npm_cache() -> str | None:
    """npm's cache location under the *real* profile, before HOME is redirected."""
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        return os.path.join(base, "npm-cache") if base else None
    return os.path.join(os.path.expanduser("~"), ".npm")


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the server and any interpreter uvx/npx spawned underneath it."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        import signal

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    proc.kill()


def live_names(
    plugin_dir: str,
    timeout: int = DEFAULT_TIMEOUT_S,
    version: str | None = None,
    placeholders: bool = False,
) -> set[str]:
    """Launch the shipped server and return the tool names it advertises."""
    spec = server_spec(plugin_dir, version=version, placeholders=placeholders)
    if spec is None:
        return set()
    argv, extra_env = spec

    # Resolve package-manager caches against the real profile *first*: the
    # isolated HOME below must not force uvx/npx to re-download every run.
    uv_cache = _default_uv_cache()
    npm_cache = _default_npm_cache()

    with tempfile.TemporaryDirectory(prefix="tool-parity-") as home:
        env = dict(os.environ)
        env.update(extra_env)
        # Clean profile: no credentials, no state carried in from the runner.
        env["HOME"] = home
        env["USERPROFILE"] = home
        env["XDG_CONFIG_HOME"] = os.path.join(home, ".config")
        env["XDG_DATA_HOME"] = os.path.join(home, ".local", "share")
        env["XDG_CACHE_HOME"] = os.path.join(home, ".cache")
        if uv_cache and not env.get("UV_CACHE_DIR"):
            env["UV_CACHE_DIR"] = uv_cache
        if npm_cache and not env.get("npm_config_cache"):
            env["npm_config_cache"] = npm_cache

        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            start_new_session=(os.name != "nt"),
        )
        stderr_tail: list[str] = []

        def drain_stderr() -> None:
            assert proc.stderr is not None
            for line in proc.stderr:
                stderr_tail.append(line.rstrip())
                del stderr_tail[:-20]

        threading.Thread(target=drain_stderr, daemon=True).start()

        def send(payload: dict) -> None:
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(payload) + "\n")
            proc.stdin.flush()

        def fail(reason: str, cls: type[RuntimeError] = RuntimeError) -> RuntimeError:
            tail = " | ".join(stderr_tail[-5:])
            return cls(f"{reason} (stderr: {tail})" if tail else reason)

        try:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "tool-parity", "version": "1"},
                    },
                }
            )
            handshake_done = False
            deadline = threading.Event()

            def expire() -> None:
                # Setting the flag is not enough to stop the wait below:
                # readline() blocks with no timeout of its own, so a server
                # that writes nothing at all never comes back to re-check the
                # loop condition and `timeout` passes unnoticed. Killing the
                # process closes stdout, which makes that readline() return ''
                # and hands control back to the loop.
                deadline.set()
                _kill_tree(proc)

            timer = threading.Timer(timeout, expire)
            timer.start()
            try:
                assert proc.stdout is not None
                while not deadline.is_set():
                    line = proc.stdout.readline()
                    if not line:
                        if deadline.is_set():
                            break
                        raise fail(
                            f"server exited before tools/list (rc={proc.poll()})"
                        )
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        message = json.loads(line)
                    except json.JSONDecodeError:
                        # Servers that leak non-protocol chatter on stdout.
                        continue
                    if message.get("id") == 1 and not handshake_done:
                        if "error" in message:
                            raise fail(f"initialize failed: {message['error']}")
                        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
                        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                        handshake_done = True
                    elif message.get("id") == 2:
                        if "error" in message:
                            raise fail(f"tools/list failed: {message['error']}")
                        return {t["name"] for t in message["result"].get("tools", [])}
                raise fail(
                    f"timed out after {timeout}s waiting for tools/list",
                    ProbeTimeout,
                )
            finally:
                timer.cancel()
        finally:
            _kill_tree(proc)
            proc.wait(timeout=30)


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------


PROBE_FAILED_HINT = (
    "this server validates its credential at startup, so a public CI runner "
    "cannot read its tool list -- the drift check for it belongs in the server "
    "repo's own CI, which has credentials (see AGENTS.md)"
)

PROBE_TIMEOUT_HINT = (
    "the server started and stayed up but never answered tools/list; the "
    "placeholder-credential retry is skipped because a hang is not a "
    "credential gate and would only cost a second full timeout"
)


def verify_plugin(
    name: str, declared_only: bool, timeout: int, version: str | None = None
) -> tuple[list[str], list[str], list[str]]:
    """Check one plugin. Returns (errors, warnings, output); errors fail the run.

    ``output`` holds the informational lines this check would print on
    success (declared names, or a live-match confirmation) -- returned rather
    than printed directly so a concurrent caller can flush them in plugin
    order instead of whichever thread happens to finish first.
    """
    plugin_dir = os.path.join(PLUGINS_DIR, name)

    if not os.path.isfile(os.path.join(plugin_dir, "tools.md")):
        # Plugins without a tool surface (agent-chat-plugin, mcp-core) have no
        # tools.md; verify_docs_current.py owns the "should it have one" call.
        return [], [], []

    declared = read_declared(plugin_dir)
    if not declared:
        return (
            [f"{name}: tools.md declares no tool names (check the page format)"],
            [],
            [],
        )

    if declared_only:
        line = (
            f"{name}: declares {len(declared)} tool(s): {', '.join(sorted(declared))}"
        )
        return [], [], [line]

    try:
        live = live_names(plugin_dir, timeout=timeout, version=version)
        note = ""
    except ProbeTimeout as exc:
        # Must precede the broad handler below: ProbeTimeout is a RuntimeError,
        # and the whole point is that this one failure does not get retried.
        return (
            [],
            [f"{name}: tool names NOT verified -- {exc}. ({PROBE_TIMEOUT_HINT})"],
            [],
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as first_exc:
        # Servers that gate stdio startup on credential presence exit before
        # tools/list. Retry once with obviously fake values (see
        # PROBE_PLACEHOLDER) -- the registry is the same either way.
        try:
            live = live_names(
                plugin_dir, timeout=timeout, version=version, placeholders=True
            )
            note = " (started with placeholder credentials)"
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            # Not a docs defect, so it does not fail the run -- but it is never
            # silent either: an unreadable server is an uncovered server.
            return (
                [],
                [
                    f"{name}: tool names NOT verified -- the server would not start. "
                    f"Without credentials: {first_exc}. With placeholders: {exc}. "
                    f"({PROBE_FAILED_HINT})"
                ],
                [],
            )

    if not live:
        return [], [], []

    errors = []
    for missing in sorted(live - declared):
        errors.append(
            f"{name}: server exposes tool '{missing}' but plugins/{name}/tools.md "
            f"does not document it (rename landed in the server, not here)"
        )
    for stale in sorted(declared - live):
        errors.append(
            f"{name}: plugins/{name}/tools.md documents tool '{stale}' but the "
            f"server does not expose it (stale name left behind after a rename)"
        )
    output = (
        [] if errors else [f"{name}: {len(live)} tool name(s) match tools.md{note}"]
    )
    return errors, [], output


def discover_plugins() -> list[str]:
    with os.scandir(PLUGINS_DIR) as entries:
        return sorted(e.name for e in entries if e.is_dir())


def _progress(message: str) -> None:
    """Trace one step on stderr, in real time.

    The report on stdout is deliberately withheld until every plugin has
    finished, which means a run killed by the CI job timeout prints nothing at
    all about where it was stuck. These lines are the trace that survives that
    kill, so they go to the other stream and are flushed on the spot --
    GitHub Actions does not flush a block-buffered pipe for us.
    """
    print(f"[parity] {message}", file=sys.stderr, flush=True)


def _check_one(
    name: str, declared_only: bool, timeout: int, version: str | None
) -> tuple[list[str], list[str], list[str]]:
    """``verify_plugin`` for one plugin, run in a worker thread by ``main``."""
    started = time.monotonic()
    _progress(f"start {name}")
    try:
        if not os.path.isdir(os.path.join(PLUGINS_DIR, name)):
            return [f"{name}: no such plugin directory"], [], []
        return verify_plugin(name, declared_only, timeout, version)
    finally:
        _progress(f"done  {name} ({time.monotonic() - started:.1f}s)")


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("plugins", nargs="*", help="plugin directory names")
    parser.add_argument("--all", action="store_true", help="check every plugin")
    parser.add_argument(
        "--declared-only",
        action="store_true",
        help="print the names tools.md declares without launching any server",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_S,
        help=f"seconds to wait for tools/list (default {DEFAULT_TIMEOUT_S})",
    )
    parser.add_argument(
        "--version",
        help=(
            "published package version to probe instead of the manifest default "
            "(use the beta to check a rename before its stable release)"
        ),
    )
    parser.add_argument(
        "--jobs",
        type=int,
        help=(
            "how many plugins to check concurrently (default: one per selected "
            "plugin, i.e. a single wave -- the wait is uvx/npx download and "
            "server startup, not CPU, so the run costs the slowest server "
            "instead of the sum of them)"
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.version and len(args.plugins) != 1:
        parser.error("--version applies to exactly one plugin")

    if args.jobs is not None and args.jobs < 1:
        parser.error("--jobs must be at least 1")

    if not os.path.isdir(PLUGINS_DIR):
        print(f"::error ::{sanitize_log(f'plugins dir not found: {PLUGINS_DIR}')}")
        return 1

    names = discover_plugins() if args.all else list(args.plugins)
    if not names:
        parser.error("pass plugin names or --all")

    # Each plugin's (errors, warnings, output) lands at its own index so the
    # results below can be flushed in plugin order regardless of which
    # worker finished first -- the report must read the same as a serial run.
    results: list[tuple[list[str], list[str], list[str]] | None] = [None] * len(names)
    workers = min(args.jobs, len(names)) if args.jobs else len(names)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_index = {
            pool.submit(
                _check_one, name, args.declared_only, args.timeout, args.version
            ): i
            for i, name in enumerate(names)
        }
        for future in as_completed(future_to_index):
            results[future_to_index[future]] = future.result()

    errors: list[str] = []
    warnings: list[str] = []
    for result in results:
        assert result is not None
        plugin_errors, plugin_warnings, plugin_output = result
        for line in plugin_output:
            print(line)
        errors.extend(plugin_errors)
        warnings.extend(plugin_warnings)

    for warning in warnings:
        print(f"::warning ::{sanitize_log(warning)}")

    if errors:
        print("\nTool-name parity errors (tools.md drifted from the live server):")
        for error in errors:
            print(f"::error ::{sanitize_log(error)}")
        return 1

    if warnings:
        print(
            f"\nTool names match for every server that could be read "
            f"({len(warnings)} server(s) unreadable -- see warnings above)."
        )
        return 0

    print("\nTool names in tools.md match the shipped servers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

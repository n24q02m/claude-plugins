#!/usr/bin/env python3
"""Unit tests for the tool-name parity gate.

Covers the parts that decide correctness without launching a server: which
names a ``tools.md`` page declares, how a package spec is pinned to a version,
and which environment a probe hands the server.
"""

import contextlib
import io
import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import verify_tool_parity as parity


class TestDeclaredNames(unittest.TestCase):
    def test_h2_headings_are_tool_names(self):
        # ``__`` separates a namespace inside one tool name; the heading is
        # kept whole, not split into two names or dropped as prose.
        md = "# Title\n\n## search\n\ntext\n\n## group__action\n"
        self.assertEqual(parity.declared_names(md.splitlines()), {"search", "group__action"})

    def test_prose_headings_are_ignored(self):
        md = "## Single-purpose memory tools\n\n## memory\n"
        self.assertEqual(parity.declared_names(md.splitlines()), {"memory"})

    def test_tool_column_table_rows_are_tool_names(self):
        md = (
            "| Tool | Purpose |\n"
            "|---|---|\n"
            "| `project` | Project-level operations |\n"
            "| `input_map` | Input action bindings |\n"
        )
        self.assertEqual(parity.declared_names(md.splitlines()), {"project", "input_map"})

    def test_action_tables_are_not_tool_names(self):
        # The per-tool tables list actions, not tools; their first column is
        # headed "Action" and must not contribute names.
        md = (
            "## search\n\n"
            "| Action | Purpose |\n"
            "|---|---|\n"
            "| `research` | Academic search |\n"
        )
        self.assertEqual(parity.declared_names(md.splitlines()), {"search"})

    def test_heading_closes_an_open_tool_table(self):
        md = (
            "| Tool | Purpose |\n"
            "|---|---|\n"
            "| `graph` | build |\n"
            "\n## query\n\n"
            "| Action | Purpose |\n"
            "|---|---|\n"
            "| `neighbors` | walk |\n"
        )
        self.assertEqual(parity.declared_names(md.splitlines()), {"graph", "query"})

    def test_real_pages_declare_names(self):
        """Every shipped MCP tools.md must parse into at least one name."""
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugins = os.path.join(here, "plugins")
        pages = 0
        for entry in sorted(os.listdir(plugins)):
            page = os.path.join(plugins, entry, "tools.md")
            if not os.path.isfile(page):
                continue
            plugin_dir = os.path.join(plugins, entry)
            remote = False
            try:
                if parity.server_spec(plugin_dir) is None:
                    continue
            except parity.RemoteEndpoint:
                remote = True  # a remote server still documents its tools here
            pages += 1
            with open(page, encoding="utf-8") as f:
                names = parity.declared_names(line.rstrip("\r\n") for line in f)
            self.assertTrue(names, f"{entry}/tools.md declared no tool names")
            self.assertIn("config", names, f"{entry}/tools.md is missing `config`")
            # `help` is a universal of the stdio servers built on the shared
            # core; HTTP-only servers (mnemo 2.20+) dropped it.
            if not remote:
                self.assertIn("help", names, f"{entry}/tools.md is missing `help`")
        self.assertGreater(pages, 0, "no tools.md pages found")


class TestPinVersion(unittest.TestCase):
    def test_bare_python_package(self):
        self.assertEqual(parity.pin_version("wet-mcp", "3.7.0b1"), "wet-mcp@3.7.0b1")

    def test_python_package_with_existing_tag(self):
        self.assertEqual(
            parity.pin_version("better-telegram-mcp@latest", "4.18.0b2"),
            "better-telegram-mcp@4.18.0b2",
        )

    def test_scoped_npm_package_keeps_its_scope(self):
        self.assertEqual(
            parity.pin_version("@n24q02m/better-email-mcp@latest", "1.38.0-beta.1"),
            "@n24q02m/better-email-mcp@1.38.0-beta.1",
        )

    def test_scoped_npm_package_without_tag(self):
        self.assertEqual(
            parity.pin_version("@n24q02m/better-godot-mcp", "1.22.0-beta.3"),
            "@n24q02m/better-godot-mcp@1.22.0-beta.3",
        )


class TestServerSpec(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir, ignore_errors=True)

    def _plugin(self, manifest):
        pdir = os.path.join(self.test_dir, "srv")
        os.makedirs(os.path.join(pdir, ".claude-plugin"), exist_ok=True)
        with open(
            os.path.join(pdir, ".claude-plugin", "plugin.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(manifest, f)
        return pdir

    def _manifest(self, **overrides):
        manifest = {
            "name": "srv",
            "userConfig": {
                "API_KEY": {"type": "string", "sensitive": True, "required": True},
                "MODEL_CHAIN": {"type": "string", "required": False},
            },
            "mcpServers": {
                "srv": {
                    "command": "uvx",
                    "args": ["--python", "3.13", "srv-mcp"],
                    "env": {
                        "MCP_TRANSPORT": "stdio",
                        "API_KEY": "${user_config.API_KEY}",
                        "MODEL_CHAIN": "${user_config.MODEL_CHAIN}",
                    },
                }
            },
        }
        manifest.update(overrides)
        return manifest

    def test_unfilled_user_config_is_dropped_not_passed_literally(self):
        pdir = self._plugin(self._manifest())
        with mock.patch.object(parity.shutil, "which", return_value=None):
            argv, env = parity.server_spec(pdir)
        self.assertEqual(argv, ["uvx", "--python", "3.13", "srv-mcp"])
        self.assertEqual(env, {"MCP_TRANSPORT": "stdio"})

    def test_placeholders_fill_only_gating_options(self):
        pdir = self._plugin(self._manifest())
        with mock.patch.object(parity.shutil, "which", return_value=None):
            _, env = parity.server_spec(pdir, placeholders=True)
        self.assertEqual(env["API_KEY"], parity.PROBE_PLACEHOLDER)
        # A tuning option is not a startup gate; junk there could break the run.
        self.assertNotIn("MODEL_CHAIN", env)

    def test_version_pins_the_package_argument(self):
        pdir = self._plugin(self._manifest())
        with mock.patch.object(parity.shutil, "which", return_value=None):
            argv, _ = parity.server_spec(pdir, version="9.9.9")
        self.assertEqual(argv, ["uvx", "--python", "3.13", "srv-mcp@9.9.9"])

    def test_plugin_without_mcp_server_has_no_spec(self):
        pdir = self._plugin(self._manifest(mcpServers={}))
        self.assertIsNone(parity.server_spec(pdir))

    def test_remote_http_entry_raises_remote_endpoint(self):
        manifest = self._manifest(
            mcpServers={
                "srv": {"type": "http", "url": "${user_config.SRV_URL}"}
            }
        )
        pdir = self._plugin(manifest)
        with self.assertRaises(parity.RemoteEndpoint) as ctx:
            parity.server_spec(pdir)
        self.assertEqual(ctx.exception.transport, "http")
        self.assertEqual(ctx.exception.url, "${user_config.SRV_URL}")

    def test_entry_without_command_or_url_is_invalid(self):
        pdir = self._plugin(self._manifest(mcpServers={"srv": {"type": "http"}}))
        with self.assertRaises(ValueError):
            parity.server_spec(pdir)

    def test_multiple_servers_rejected(self):
        manifest = self._manifest(
            mcpServers={"a": {"command": "x"}, "b": {"command": "y"}}
        )
        pdir = self._plugin(manifest)
        with self.assertRaises(ValueError):
            parity.server_spec(pdir)


class TestProbeTimeout(unittest.TestCase):
    def test_a_silent_server_is_cut_off_at_the_timeout(self):
        # The failure this guards: a server that accepts the handshake and
        # then writes nothing leaves readline() blocked forever, so `timeout`
        # elapses unnoticed and only the CI job timeout ends the run.
        test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, test_dir, ignore_errors=True)
        pdir = os.path.join(test_dir, "srv")
        os.makedirs(os.path.join(pdir, ".claude-plugin"))
        with open(
            os.path.join(pdir, ".claude-plugin", "plugin.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(
                {
                    "name": "srv",
                    "mcpServers": {
                        "srv": {
                            "command": sys.executable,
                            "args": ["-c", "import time; time.sleep(300)"],
                        }
                    },
                },
                f,
            )

        started = time.monotonic()
        with self.assertRaises(parity.ProbeTimeout):
            parity.live_names(pdir, timeout=2)
        # Generous, because it only has to prove the wait is bounded at all.
        self.assertLess(time.monotonic() - started, 60)


class TestVerifyPlugin(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        os.makedirs(os.path.join("plugins", "srv", ".claude-plugin"))
        self.addCleanup(shutil.rmtree, self.test_dir, ignore_errors=True)
        self.addCleanup(os.chdir, self.old_cwd)
        with open(
            os.path.join("plugins", "srv", ".claude-plugin", "plugin.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                {"name": "srv", "mcpServers": {"srv": {"command": "srv-mcp"}}}, f
            )

    def _write_tools_md(self, body):
        with open(os.path.join("plugins", "srv", "tools.md"), "w", encoding="utf-8") as f:
            f.write(body)

    def test_matching_names_pass(self):
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity, "live_names", return_value={"search", "config", "help"}
        ):
            errors, warnings, output = parity.verify_plugin("srv", False, 10)
        self.assertEqual((errors, warnings), ([], []))
        self.assertEqual(len(output), 1)
        self.assertIn("3 tool name(s) match tools.md", output[0])

    def test_renamed_tool_is_an_error(self):
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity, "live_names", return_value={"search_web", "config", "help"}
        ):
            errors, warnings, output = parity.verify_plugin("srv", False, 10)
        self.assertEqual(warnings, [])
        self.assertEqual(output, [])
        joined = "\n".join(errors)
        self.assertIn("search_web", joined)
        self.assertIn("search", joined)
        self.assertEqual(len(errors), 2, joined)

    def test_unreadable_server_warns_but_does_not_fail(self):
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity, "live_names", side_effect=RuntimeError("server exited")
        ):
            errors, warnings, output = parity.verify_plugin("srv", False, 10)
        self.assertEqual(errors, [])
        self.assertEqual(output, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("NOT verified", warnings[0])

    def test_credential_gate_is_still_retried_with_placeholders(self):
        # The retry this class of failure exists for: the server refuses to
        # start without a credential, and placeholders get past that gate.
        self._write_tools_md("## search\n\n## config\n\n## help\n")

        def gated(plugin_dir, timeout, version=None, placeholders=False):
            if not placeholders:
                raise RuntimeError("server exited before tools/list (rc=1)")
            return {"search", "config", "help"}

        with mock.patch.object(parity, "live_names", side_effect=gated) as live:
            errors, warnings, output = parity.verify_plugin("srv", False, 10)
        self.assertEqual((errors, warnings), ([], []))
        self.assertIn("placeholder credentials", output[0])
        self.assertEqual(live.call_count, 2)

    def test_timeout_is_not_retried_with_placeholders(self):
        # A hang is not a credential gate. Retrying would hang identically and
        # cost a second full timeout, which is what overran the CI budget.
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity,
            "live_names",
            side_effect=parity.ProbeTimeout("timed out after 10s"),
        ) as live:
            errors, warnings, output = parity.verify_plugin("srv", False, 10)
        self.assertEqual((errors, output), ([], []))
        self.assertEqual(len(warnings), 1)
        self.assertIn("timed out after 10s", warnings[0])
        self.assertEqual(live.call_count, 1)

    def test_portable_non_mcp_tools_page_is_skipped(self):
        manifest = os.path.join(
            "plugins", "srv", ".claude-plugin", "plugin.json"
        )
        with open(manifest, "w", encoding="utf-8") as stream:
            json.dump({"name": "srv", "mcpServers": {}}, stream)
        self._write_tools_md(
            "# Commands\n\n| Surface | Commands |\n|---|---|\n| Tasks | `task create` |\n"
        )

        with mock.patch.object(
            parity, "live_names", side_effect=AssertionError("must not be called")
        ):
            result = parity.verify_plugin("srv", False, 10)

        self.assertEqual(result, ([], [], []))

    def _make_remote(self):
        manifest = os.path.join("plugins", "srv", ".claude-plugin", "plugin.json")
        with open(manifest, "w", encoding="utf-8") as stream:
            json.dump(
                {
                    "name": "srv",
                    "mcpServers": {
                        "srv": {"type": "http", "url": "${user_config.SRV_URL}"}
                    },
                },
                stream,
            )

    def test_remote_server_warns_without_launching(self):
        self._make_remote()
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity, "live_names", side_effect=AssertionError("must not be called")
        ):
            errors, warnings, output = parity.verify_plugin("srv", False, 10)
        self.assertEqual((errors, output), ([], []))
        self.assertEqual(len(warnings), 1)
        self.assertIn("NOT verified", warnings[0])
        self.assertIn("remote http endpoint", warnings[0])

    def test_remote_server_still_checks_declared_names(self):
        self._make_remote()
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        errors, warnings, output = parity.verify_plugin("srv", True, 10)
        self.assertEqual((errors, warnings), ([], []))
        self.assertIn("declares 3 tool(s)", output[0])

    def test_remote_server_with_unparseable_page_is_an_error(self):
        self._make_remote()
        self._write_tools_md("# Tools\n\nProse only, no tool names.\n")
        errors, _, _ = parity.verify_plugin("srv", False, 10)
        self.assertEqual(len(errors), 1)
        self.assertIn("declares no tool names", errors[0])

    def test_unparseable_page_is_an_error(self):
        self._write_tools_md("# Tools\n\nProse only, no tool names.\n")
        errors, warnings, output = parity.verify_plugin("srv", True, 10)
        self.assertEqual(warnings, [])
        self.assertEqual(output, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("declares no tool names", errors[0])

    def test_plugin_without_tools_md_is_skipped(self):
        errors, warnings, output = parity.verify_plugin("srv", False, 10)
        self.assertEqual((errors, warnings, output), ([], [], []))

    def test_declared_only_never_launches_a_server(self):
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity, "live_names", side_effect=AssertionError("must not be called")
        ):
            errors, warnings, output = parity.verify_plugin("srv", True, 10)
        self.assertEqual((errors, warnings), ([], []))
        self.assertEqual(len(output), 1)
        self.assertIn("declares 3 tool(s)", output[0])


class TestMain(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        os.makedirs(os.path.join("plugins", "srv"))
        self.addCleanup(shutil.rmtree, self.test_dir, ignore_errors=True)
        self.addCleanup(os.chdir, self.old_cwd)

    def test_unknown_plugin_fails(self):
        self.assertEqual(parity.main(["nope"]), 1)

    def test_version_requires_exactly_one_plugin(self):
        with self.assertRaises(SystemExit):
            parity.main(["--all", "--version", "1.0.0"])

    def test_no_plugins_selected_is_a_usage_error(self):
        with self.assertRaises(SystemExit):
            parity.main([])

    def test_jobs_must_be_positive(self):
        with self.assertRaises(SystemExit):
            parity.main(["srv", "--jobs", "0"])

    def test_jobs_must_be_less_than_1024(self):
        with self.assertRaises(SystemExit):
            parity.main(["srv", "--jobs", "2000"])

    def test_timeout_must_be_positive(self):
        with self.assertRaises(SystemExit):
            parity.main(["srv", "--timeout", "0"])

    def test_version_max_length(self):
        with self.assertRaises(SystemExit):
            parity.main(["srv", "--version", "a" * 129])

    def test_plugin_max_length(self):
        with self.assertRaises(SystemExit):
            parity.main(["a" * 129])

    def _max_workers_for(self, argv):
        with mock.patch.object(parity, "verify_plugin", return_value=([], [], [])):
            with mock.patch.object(
                parity, "ThreadPoolExecutor", wraps=parity.ThreadPoolExecutor
            ) as pool:
                self.assertEqual(parity.main(argv), 0)
        return pool.call_args.kwargs["max_workers"]

    def test_every_plugin_is_probed_in_one_wave_by_default(self):
        # Worst-case wall time is then the slowest server, not ceil(n/jobs)
        # waves of it -- that arithmetic has to fit the CI job timeout.
        self.assertEqual(self._max_workers_for(["srv", "srv", "srv"]), 3)

    def test_explicit_jobs_still_throttles(self):
        self.assertEqual(self._max_workers_for(["srv", "srv", "srv", "--jobs", "2"]), 2)

    def test_warning_only_run_succeeds(self):
        with mock.patch.object(
            parity, "verify_plugin", return_value=([], ["srv: unreadable"], [])
        ):
            self.assertEqual(parity.main(["srv"]), 0)

    def test_output_prints_in_plugin_order_not_completion_order(self):
        # Plugins run concurrently, so the slowest one must not be allowed to
        # print last-in-completion-order -- the transcript has to read in the
        # order main() was given the plugins, exactly like a serial run.
        for pname in ("aaa", "bbb", "ccc"):
            os.makedirs(os.path.join("plugins", pname), exist_ok=True)
        delays = {"aaa": 0.06, "bbb": 0.0, "ccc": 0.03}

        def fake_verify(name, declared_only, timeout, version=None):
            time.sleep(delays[name])
            return [], [], [f"{name}: ok"]

        buf = io.StringIO()
        with mock.patch.object(parity, "verify_plugin", side_effect=fake_verify):
            with contextlib.redirect_stdout(buf):
                rc = parity.main(["aaa", "bbb", "ccc", "--jobs", "3"])
        self.assertEqual(rc, 0)
        lines = [line for line in buf.getvalue().splitlines() if line.endswith(": ok")]
        self.assertEqual(lines, ["aaa: ok", "bbb: ok", "ccc: ok"])


# A stand-in MCP server, launched for real over stdio by live_names(). The mode
# (argv[1]) picks how it behaves; the remaining arguments are the tool names it
# advertises.
FAKE_SERVER = r'''
import json
import os
import sys

mode, tools = sys.argv[1], sys.argv[2:]


def reply(message):
    print(json.dumps(message), flush=True)


print("fake server starting", file=sys.stderr, flush=True)
if mode == "exit" or (mode == "gated" and not os.environ.get("API_KEY")):
    print("API_KEY is not set; refusing to start", file=sys.stderr, flush=True)
    sys.exit(3)
if mode == "env":
    tools = [
        f"{key}={os.environ.get(key)}"
        for key in ("HOME", "MCP_TRANSPORT", "UV_CACHE_DIR", "npm_config_cache")
    ]

while True:
    line = sys.stdin.readline()
    if not line:
        break
    request = json.loads(line)
    if request.get("method") == "initialize":
        if mode == "init-error":
            reply({"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "boom"}})
            continue
        if mode == "chatter":
            while True:
                print("still warming up", flush=True)
        # Noise a real server may emit before answering: a blank line, a log
        # line on stdout, and a notification that carries no id.
        print("", flush=True)
        print("listening on stdio", flush=True)
        reply({"jsonrpc": "2.0", "method": "notifications/message", "params": {}})
        reply({"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}})
    elif request.get("method") == "tools/list":
        if mode == "list-error":
            reply({"jsonrpc": "2.0", "id": 2, "error": {"code": -32601, "message": "nope"}})
            continue
        reply({"jsonrpc": "2.0", "id": 2, "result": {"tools": [{"name": t} for t in tools]}})
'''


class FakeServerTestCase(unittest.TestCase):
    """A temp checkout whose plugin runs FAKE_SERVER with this interpreter."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir, ignore_errors=True)
        old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        self.addCleanup(os.chdir, old_cwd)
        self.server = os.path.join(self.test_dir, "fake_server.py")
        with open(self.server, "w", encoding="utf-8") as f:
            f.write(FAKE_SERVER)
        self.pdir = os.path.join("plugins", "srv")
        os.makedirs(os.path.join(self.pdir, ".claude-plugin"))

    def _manifest(self, mode, *tools, **entry):
        server = {"command": sys.executable, "args": [self.server, mode, *tools]}
        server.update(entry)
        manifest = {"name": "srv", "mcpServers": {"srv": server}}
        with open(
            os.path.join(self.pdir, ".claude-plugin", "plugin.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(manifest, f)

    def _tools_md(self, body):
        with open(os.path.join(self.pdir, "tools.md"), "w", encoding="utf-8") as f:
            f.write(body)

    def _main(self, *argv):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = parity.main(list(argv))
        return rc, out.getvalue().splitlines()


class TestLiveProbe(FakeServerTestCase):
    def test_reads_tool_names_past_startup_noise(self):
        self._manifest("ok", "search", "config")
        self.assertEqual(parity.live_names(self.pdir, timeout=60), {"search", "config"})

    def test_server_exiting_early_reports_its_stderr(self):
        self._manifest("exit")
        with self.assertRaises(RuntimeError) as cm:
            parity.live_names(self.pdir, timeout=60)
        self.assertNotIsInstance(cm.exception, parity.ProbeTimeout)
        message = str(cm.exception)
        self.assertTrue(
            message.startswith("server exited before tools/list (rc="), message
        )
        self.assertIn("API_KEY is not set; refusing to start", message)

    def test_initialize_error_is_reported(self):
        self._manifest("init-error")
        with self.assertRaisesRegex(RuntimeError, "^initialize failed: .*boom"):
            parity.live_names(self.pdir, timeout=60)

    def test_tools_list_error_is_reported(self):
        self._manifest("list-error")
        with self.assertRaisesRegex(RuntimeError, "^tools/list failed: .*nope"):
            parity.live_names(self.pdir, timeout=60)

    def test_server_that_only_chatters_is_cut_off_at_the_timeout(self):
        # The opposite of a silent server: one that keeps writing lines that
        # are not the answer must hit the same bound.
        self._manifest("chatter")
        started = time.monotonic()
        with self.assertRaises(parity.ProbeTimeout):
            parity.live_names(self.pdir, timeout=2)
        self.assertLess(time.monotonic() - started, 60)

    def test_server_gets_an_isolated_profile_and_the_real_caches(self):
        self._manifest("env")
        with mock.patch.dict(os.environ):
            os.environ.pop("UV_CACHE_DIR", None)
            os.environ.pop("npm_config_cache", None)
            names = parity.live_names(self.pdir, timeout=60)
            uv_cache = parity._default_uv_cache()
            npm_cache = parity._default_npm_cache()

        env = dict(name.split("=", 1) for name in names)
        self.assertNotEqual(env["HOME"], os.path.expanduser("~"))
        self.assertTrue(
            os.path.basename(env["HOME"]).startswith("tool-parity-"), env["HOME"]
        )
        self.assertEqual(env["MCP_TRANSPORT"], "stdio")
        self.assertEqual(env["UV_CACHE_DIR"], str(uv_cache))
        self.assertEqual(env["npm_config_cache"], str(npm_cache))

    def test_a_preset_uv_cache_is_kept(self):
        self._manifest("env")
        preset = os.path.join(self.test_dir, "uv-cache")
        with mock.patch.dict(os.environ, {"UV_CACHE_DIR": preset}):
            names = parity.live_names(self.pdir, timeout=60)
        self.assertIn(f"UV_CACHE_DIR={preset}", names)

    def test_plugin_without_mcp_server_has_no_live_names(self):
        with open(
            os.path.join(self.pdir, ".claude-plugin", "plugin.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump({"name": "srv"}, f)
        self.assertEqual(parity.live_names(self.pdir, timeout=60), set())


class TestEndToEnd(FakeServerTestCase):
    def test_matching_server_passes(self):
        self._manifest("ok", "search", "config")
        self._tools_md("# Tools\n\n## search\n\n## config\n")

        rc, lines = self._main("srv", "--timeout", "60")

        self.assertEqual(rc, 0)
        self.assertEqual(
            lines,
            [
                "srv: 2 tool name(s) match tools.md",
                "",
                "Tool names in tools.md match the shipped servers.",
            ],
        )

    def test_renamed_tool_fails_the_run(self):
        self._manifest("ok", "search", "settings")
        self._tools_md("## search\n\n## config\n")

        rc, lines = self._main("srv", "--timeout", "60")

        self.assertEqual(rc, 1)
        self.assertIn(
            "::error ::srv: server exposes tool 'settings' but plugins/srv/tools.md "
            "does not document it (rename landed in the server, not here)",
            lines,
        )
        self.assertIn(
            "::error ::srv: plugins/srv/tools.md documents tool 'config' but the "
            "server does not expose it (stale name left behind after a rename)",
            lines,
        )

    def test_credential_gated_server_is_read_with_placeholders(self):
        self._manifest(
            "gated", "search", env={"API_KEY": "${user_config.API_KEY}"}
        )
        with open(
            os.path.join(self.pdir, ".claude-plugin", "plugin.json"), encoding="utf-8"
        ) as f:
            manifest = json.load(f)
        manifest["userConfig"] = {"API_KEY": {"type": "string", "sensitive": True}}
        with open(
            os.path.join(self.pdir, ".claude-plugin", "plugin.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(manifest, f)
        self._tools_md("## search\n")

        with mock.patch.dict(os.environ):
            os.environ.pop("API_KEY", None)
            errors, warnings, output = parity.verify_plugin("srv", False, 60)

        self.assertEqual((errors, warnings), ([], []))
        self.assertEqual(
            output,
            ["srv: 1 tool name(s) match tools.md (started with placeholder credentials)"],
        )

    def test_server_with_no_tools_is_not_compared(self):
        self._manifest("ok")
        self._tools_md("## search\n")
        self.assertEqual(parity.verify_plugin("srv", False, 60), ([], [], []))

    def test_unparseable_manifest_is_an_error(self):
        with open(
            os.path.join(self.pdir, ".claude-plugin", "plugin.json"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write("{not json")
        self._tools_md("## search\n")

        errors, warnings, output = parity.verify_plugin("srv", True, 60)

        self.assertEqual(len(errors), 1)
        self.assertTrue(
            errors[0].startswith("srv: invalid MCP server manifest: "), errors
        )

    def test_all_discovers_plugin_directories(self):
        self._manifest("ok", "search")
        self._tools_md("## search\n")
        with open(os.path.join("plugins", "README.md"), "w", encoding="utf-8") as f:
            f.write("not a plugin")
        os.makedirs(os.path.join("plugins", "docs-only"))

        rc, lines = self._main("--all", "--declared-only")

        self.assertEqual(rc, 0)
        self.assertEqual(lines[0], "srv: declares 1 tool(s): search")

    def test_missing_plugins_dir_fails(self):
        shutil.rmtree("plugins")
        rc, lines = self._main("srv")
        self.assertEqual(rc, 1)
        self.assertEqual(lines, ["::error ::plugins dir not found: plugins"])

    def test_runs_as_a_script(self):
        self._manifest("ok", "search")
        self._tools_md("## search\n")
        script = os.path.join(
            os.path.dirname(os.path.abspath(parity.__file__)), "verify_tool_parity.py"
        )
        out = io.StringIO()
        with mock.patch.object(sys, "argv", [script, "--all", "--declared-only"]):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(
                io.StringIO()
            ):
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(script, run_name="__main__")
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("srv: declares 1 tool(s): search", out.getvalue())


class TestDeclaredTableRows(unittest.TestCase):
    def test_non_tool_rows_in_a_tool_table_are_skipped(self):
        lines = [
            "| Tool | Purpose |",
            "|------|---------|",
            "| `search` | find things |",
            "| see the section below | prose, not a tool |",
        ]
        self.assertEqual(parity.declared_names(lines), {"search"})


class TestVersionPinning(unittest.TestCase):
    def test_version_needs_a_package_argument(self):
        test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, test_dir, ignore_errors=True)
        os.makedirs(os.path.join(test_dir, ".claude-plugin"))
        with open(
            os.path.join(test_dir, ".claude-plugin", "plugin.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                {"mcpServers": {"srv": {"command": "npx", "args": ["--yes"]}}}, f
            )
        with self.assertRaisesRegex(ValueError, "no package argument"):
            parity.server_spec(test_dir, version="1.2.3")


class TestPackageCaches(unittest.TestCase):
    """Where uvx/npx keep their caches before HOME is redirected, per OS."""

    def test_windows_layout(self):
        env = {"LOCALAPPDATA": os.path.join("L", "AppData"), "APPDATA": "R"}
        with mock.patch.object(parity.os, "name", "nt"):
            with mock.patch.dict(os.environ, env):
                uv_cache = parity._default_uv_cache()
                npm_cache = parity._default_npm_cache()
            with mock.patch.dict(os.environ):
                os.environ.pop("LOCALAPPDATA", None)
                os.environ.pop("APPDATA", None)
                missing = (parity._default_uv_cache(), parity._default_npm_cache())
        self.assertEqual(uv_cache, os.path.join("L", "AppData", "uv", "cache"))
        self.assertEqual(npm_cache, os.path.join("R", "npm-cache"))
        self.assertEqual(missing, (None, None))

    def test_posix_layout(self):
        home = os.path.expanduser("~")
        with mock.patch.object(parity.os, "name", "posix"):
            with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "xdg"}):
                xdg_uv = parity._default_uv_cache()
            with mock.patch.dict(os.environ):
                os.environ.pop("XDG_CACHE_HOME", None)
                default_uv = parity._default_uv_cache()
                npm_cache = parity._default_npm_cache()
        self.assertEqual(xdg_uv, os.path.join("xdg", "uv"))
        self.assertEqual(default_uv, os.path.join(home, ".cache", "uv"))
        self.assertEqual(npm_cache, os.path.join(home, ".npm"))


class TestKillTree(unittest.TestCase):
    def _spawn(self, code):
        # Own process group on POSIX: _kill_tree kills the whole group, which
        # must never be the test runner's.
        return subprocess.Popen(
            [sys.executable, "-c", code], start_new_session=(os.name != "nt")
        )

    def test_exited_process_is_left_alone(self):
        proc = self._spawn("pass")
        proc.wait(timeout=60)
        parity._kill_tree(proc)
        self.assertEqual(proc.returncode, 0)

    def test_running_process_is_killed(self):
        proc = self._spawn("import time; time.sleep(120)")
        self.addCleanup(proc.wait, 30)
        parity._kill_tree(proc)
        self.assertNotEqual(proc.wait(timeout=30), 0)

    def test_vanished_process_group_still_kills_the_process(self):
        # The group can be gone by the time it is looked up (the server
        # exited between poll() and getpgid()); the process itself is then
        # still killed.
        proc = self._spawn("import time; time.sleep(120)")
        self.addCleanup(proc.wait, 30)
        with mock.patch.object(parity.os, "name", "posix"), mock.patch.object(
            parity.os, "getpgid", side_effect=ProcessLookupError, create=True
        ), mock.patch.object(parity.os, "killpg", create=True) as killpg:
            parity._kill_tree(proc)
        killpg.assert_not_called()
        self.assertNotEqual(proc.wait(timeout=30), 0)


class TestCheckOne(unittest.TestCase):
    def test_missing_plugin_directory_is_an_error(self):
        test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, test_dir, ignore_errors=True)
        old_cwd = os.getcwd()
        os.chdir(test_dir)
        self.addCleanup(os.chdir, old_cwd)
        with contextlib.redirect_stderr(io.StringIO()) as err:
            result = parity._check_one("absent", True, 60, None)
        self.assertEqual(result, (["absent: no such plugin directory"], [], []))
        self.assertIn("[parity] start absent", err.getvalue())
        self.assertIn("[parity] done  absent", err.getvalue())


if __name__ == "__main__":
    unittest.main()

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
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

import verify_tool_parity as parity


class TestDeclaredNames(unittest.TestCase):
    def test_h2_headings_are_tool_names(self):
        md = "# Title\n\n## search\n\ntext\n\n## config__open_relay\n"
        self.assertEqual(parity.declared_names(md), {"search", "config__open_relay"})

    def test_prose_headings_are_ignored(self):
        md = "## Single-purpose memory tools\n\n## memory\n"
        self.assertEqual(parity.declared_names(md), {"memory"})

    def test_tool_column_table_rows_are_tool_names(self):
        md = (
            "| Tool | Purpose |\n"
            "|---|---|\n"
            "| `project` | Project-level operations |\n"
            "| `input_map` | Input action bindings |\n"
        )
        self.assertEqual(parity.declared_names(md), {"project", "input_map"})

    def test_action_tables_are_not_tool_names(self):
        # The per-tool tables list actions, not tools; their first column is
        # headed "Action" and must not contribute names.
        md = (
            "## search\n\n"
            "| Action | Purpose |\n"
            "|---|---|\n"
            "| `research` | Academic search |\n"
        )
        self.assertEqual(parity.declared_names(md), {"search"})

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
        self.assertEqual(parity.declared_names(md), {"graph", "query"})

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
            if parity.server_spec(plugin_dir) is None:
                continue
            pages += 1
            with open(page, encoding="utf-8") as f:
                names = parity.declared_names(f.read())
            self.assertTrue(names, f"{entry}/tools.md declared no tool names")
            # help and config are the two universals every server ships.
            self.assertIn("help", names, f"{entry}/tools.md is missing `help`")
            self.assertIn("config", names, f"{entry}/tools.md is missing `config`")
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


if __name__ == "__main__":
    unittest.main()

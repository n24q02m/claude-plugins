#!/usr/bin/env python3
"""Unit tests for the tool-name parity gate.

Covers the parts that decide correctness without launching a server: which
names a ``tools.md`` page declares, how a package spec is pinned to a version,
and which environment a probe hands the server.
"""

import json
import os
import shutil
import tempfile
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
        """Every shipped tools.md must parse into at least one name."""
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        plugins = os.path.join(here, "plugins")
        pages = 0
        for entry in sorted(os.listdir(plugins)):
            page = os.path.join(plugins, entry, "tools.md")
            if not os.path.isfile(page):
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
            errors, warnings = parity.verify_plugin("srv", False, 10)
        self.assertEqual((errors, warnings), ([], []))

    def test_renamed_tool_is_an_error(self):
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity, "live_names", return_value={"search_web", "config", "help"}
        ):
            errors, warnings = parity.verify_plugin("srv", False, 10)
        self.assertEqual(warnings, [])
        joined = "\n".join(errors)
        self.assertIn("search_web", joined)
        self.assertIn("search", joined)
        self.assertEqual(len(errors), 2, joined)

    def test_unreadable_server_warns_but_does_not_fail(self):
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity, "live_names", side_effect=RuntimeError("server exited")
        ):
            errors, warnings = parity.verify_plugin("srv", False, 10)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("NOT verified", warnings[0])

    def test_unparseable_page_is_an_error(self):
        self._write_tools_md("# Tools\n\nProse only, no tool names.\n")
        errors, warnings = parity.verify_plugin("srv", True, 10)
        self.assertEqual(warnings, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("declares no tool names", errors[0])

    def test_plugin_without_tools_md_is_skipped(self):
        errors, warnings = parity.verify_plugin("srv", False, 10)
        self.assertEqual((errors, warnings), ([], []))

    def test_declared_only_never_launches_a_server(self):
        self._write_tools_md("## search\n\n## config\n\n## help\n")
        with mock.patch.object(
            parity, "live_names", side_effect=AssertionError("must not be called")
        ):
            errors, warnings = parity.verify_plugin("srv", True, 10)
        self.assertEqual((errors, warnings), ([], []))


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

    def test_warning_only_run_succeeds(self):
        with mock.patch.object(
            parity, "verify_plugin", return_value=([], ["srv: unreadable"])
        ):
            self.assertEqual(parity.main(["srv"]), 0)


if __name__ == "__main__":
    unittest.main()

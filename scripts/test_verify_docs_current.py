#!/usr/bin/env python3
"""Unit tests for the verify_docs_current gate (WS-E / E6)."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import verify_docs_current


class TestVerifyDocsCurrent(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        os.makedirs("plugins")

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _make_plugin(self, name, *, mcp=True, user_config=None, docs=None):
        pdir = os.path.join("plugins", name)
        os.makedirs(os.path.join(pdir, ".claude-plugin"))
        manifest = {"name": name, "description": "d"}
        if mcp:
            manifest["mcpServers"] = {name: {"command": "x"}}
        if user_config is not None:
            manifest["userConfig"] = user_config
        with open(
            os.path.join(pdir, ".claude-plugin", "plugin.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(manifest, f)
        for doc, body in (docs or {}).items():
            with open(os.path.join(pdir, doc), "w", encoding="utf-8") as f:
                f.write(body)
        return pdir

    def _full_docs(self, extra=""):
        return {doc: f"# {doc}\n{extra}" for doc in verify_docs_current.REQUIRED_DOCS}

    def test_complete_server_passes(self):
        self._make_plugin(
            "srv",
            user_config={"API_KEY": {"type": "string"}},
            docs=self._full_docs(extra="Set API_KEY to enable."),
        )
        # Success path returns normally (no sys.exit).
        verify_docs_current.verify_docs_current()

    def test_missing_required_doc_fails(self):
        docs = self._full_docs()
        docs.pop("troubleshooting.md")
        self._make_plugin("srv", user_config={}, docs=docs)
        with self.assertRaises(SystemExit) as cm:
            verify_docs_current.verify_docs_current()
        self.assertEqual(cm.exception.code, 1)

    def test_undocumented_userconfig_fails(self):
        self._make_plugin(
            "srv",
            user_config={"NEW_KEY": {"type": "string"}},
            docs=self._full_docs(extra="no mention here"),
        )
        with self.assertRaises(SystemExit) as cm:
            verify_docs_current.verify_docs_current()
        self.assertEqual(cm.exception.code, 1)

    def test_foundation_without_mcpservers_skipped(self):
        # No mcpServers manifest + no docs -> not a runnable server, must pass.
        self._make_plugin("mcp-core", mcp=False, docs={"architecture.md": "# arch"})
        # Success path returns normally (no sys.exit).
        verify_docs_current.verify_docs_current()


class TestDistributionLifecycleDocs(unittest.TestCase):
    """Repository contracts for retired hosted/OCI distribution surfaces."""

    root = Path(__file__).resolve().parents[1]

    def _read(self, relative: str) -> str:
        return (self.root / relative).read_text(encoding="utf-8")

    def test_sunset_oci_plugins_document_source_builds_without_current_aliases(self):
        retired_aliases = {
            "wet-mcp": (
                "n24q02m/wet-mcp:latest",
                "ghcr.io/n24q02m/wet-mcp",
                "docker.io/n24q02m/wet-mcp",
            ),
            "mnemo-mcp": (
                "n24q02m/mnemo-mcp:latest",
                "ghcr.io/n24q02m/mnemo-mcp",
                "docker.io/n24q02m/mnemo-mcp",
            ),
            "better-code-review-graph": (
                "n24q02m/better-code-review-graph:latest",
                "ghcr.io/n24q02m/better-code-review-graph",
                "docker.io/n24q02m/better-code-review-graph",
            ),
        }

        for plugin, aliases in retired_aliases.items():
            plugin_dir = self.root / "plugins" / plugin
            docs = "\n".join(
                path.read_text(encoding="utf-8") for path in plugin_dir.glob("*.md")
            )
            for alias in aliases:
                self.assertNotIn(alias, docs, f"{plugin} still recommends {alias}")
            self.assertIn("build", docs.lower())

        comparison = self._read(
            "docs/src/content/docs/reference/server-comparison.md"
        )
        for plugin in retired_aliases:
            row = next(
                line for line in comparison.splitlines() if f"`{plugin}`" in line
            )
            self.assertIn("Source build", row)
            self.assertNotIn("GHCR", row)

    def test_telegram_defaults_to_stdio_and_marks_hosted_runtime_retired(self):
        manifest = json.loads(
            self._read(
                "plugins/better-telegram-mcp/.claude-plugin/plugin.json"
            )
        )
        server = manifest["mcpServers"]["better-telegram-mcp"]
        self.assertEqual(server["command"], "uvx")
        self.assertEqual(server["env"]["MCP_TRANSPORT"], "stdio")

        overview = self._read("plugins/better-telegram-mcp/overview.md")
        self.assertIn("Defaults to local stdio", overview)
        self.assertIn("hosted runtime is retired", overview)
        self.assertNotIn("Defaults to a team-shared remote deployment", overview)

        mode_matrix = self._read(
            "docs/src/content/docs/reference/mode-matrix.md"
        )
        telegram_row = next(
            line
            for line in mode_matrix.splitlines()
            if "`better-telegram-mcp`" in line
        )
        self.assertTrue(telegram_row.rstrip().endswith("| `stdio` |"))

    def test_public_docs_do_not_claim_every_server_publishes_oci(self):
        index = self._read("docs/src/content/docs/index.mdx")
        llms = self._read("docs/public/llms.txt")

        self.assertNotIn("signed Docker images", index)
        self.assertNotIn("Each server ships", llms)
        self.assertIn("Source-built containers", llms)


if __name__ == "__main__":
    unittest.main()

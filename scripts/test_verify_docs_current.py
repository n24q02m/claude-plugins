#!/usr/bin/env python3
"""Unit tests for the verify_docs_current gate (WS-E / E6)."""

import json
import os
import shutil
import tempfile
import unittest

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

    def test_discontinued_wet_public_image_claim_fails(self):
        self._make_plugin(
            "wet-mcp",
            user_config={},
            docs=self._full_docs(extra="docker pull n24q02m/wet-mcp:latest"),
        )

        with self.assertRaises(SystemExit) as cm:
            verify_docs_current.verify_docs_current()

        self.assertEqual(cm.exception.code, 1)

    def test_discontinued_wet_public_image_claim_in_docs_site_fails(self):
        self._make_plugin("wet-mcp", user_config={}, docs=self._full_docs())
        docs_dir = os.path.join("docs", "src", "content", "docs", "reference")
        os.makedirs(docs_dir)
        with open(
            os.path.join(docs_dir, "self-host.md"), "w", encoding="utf-8"
        ) as f:
            f.write("image: ghcr.io/n24q02m/wet-mcp:latest")

        with self.assertRaises(SystemExit) as cm:
            verify_docs_current.verify_docs_current()

        self.assertEqual(cm.exception.code, 1)

    def test_discontinued_crg_public_image_claim_fails(self):
        self._make_plugin(
            "better-code-review-graph",
            user_config={},
            docs=self._full_docs(
                extra="docker pull n24q02m/better-code-review-graph:latest"
            ),
        )

        with self.assertRaises(SystemExit) as cm:
            verify_docs_current.verify_docs_current()

        self.assertEqual(cm.exception.code, 1)

    def test_wet_cross_plugin_docker_denial_claim_fails(self):
        self._make_plugin(
            "wet-mcp",
            user_config={},
            docs=self._full_docs(
                extra="The other plugins don't ship Docker / HTTP variants."
            ),
        )

        with self.assertRaises(SystemExit) as cm:
            verify_docs_current.verify_docs_current()

        self.assertEqual(cm.exception.code, 1)

    def test_source_built_docker_denial_claim_fails(self):
        for plugin in ("better-code-review-graph", "better-godot-mcp"):
            with self.subTest(plugin=plugin):
                self._make_plugin(
                    plugin,
                    user_config={},
                    docs=self._full_docs(
                        extra="This server doesn't ship Docker or HTTP variants."
                    ),
                )

                with self.assertRaises(SystemExit) as cm:
                    verify_docs_current.verify_docs_current()

                self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()

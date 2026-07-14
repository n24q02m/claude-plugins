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
        with open(os.path.join(pdir, ".claude-plugin", "plugin.json"), "w", encoding="utf-8") as f:
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


if __name__ == "__main__":
    unittest.main()

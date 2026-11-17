#!/usr/bin/env python3
"""Unit tests for the verify_docs_current gate (WS-E / E6)."""

import builtins
import contextlib
import io
import json
import os
import runpy
import shutil
import tempfile
import unittest
from unittest import mock

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
        self._make_plugin("hull", mcp=False, docs={"architecture.md": "# arch"})
        # Success path returns normally (no sys.exit).
        verify_docs_current.verify_docs_current()

    def test_discontinued_wet_public_image_claim_fails(self):
        self._make_plugin(
            "wet",
            user_config={},
            docs=self._full_docs(extra="docker pull n24q02m/wet-mcp:latest"),
        )

        with self.assertRaises(SystemExit) as cm:
            verify_docs_current.verify_docs_current()

        self.assertEqual(cm.exception.code, 1)

    def test_discontinued_wet_public_image_claim_in_docs_site_fails(self):
        self._make_plugin("wet", user_config={}, docs=self._full_docs())
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
            "crg",
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
            "wet",
            user_config={},
            docs=self._full_docs(
                extra="The other plugins don't ship Docker / HTTP variants."
            ),
        )

        with self.assertRaises(SystemExit) as cm:
            verify_docs_current.verify_docs_current()

        self.assertEqual(cm.exception.code, 1)

    def test_source_built_docker_denial_claim_fails(self):
        for plugin in ("crg", "better-godot-mcp"):
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


    def _run(self):
        """Run the gate; return (exit code or None, printed lines)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                verify_docs_current.verify_docs_current()
                code = None
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue().splitlines()

    def test_unreadable_doc_page_is_reported_not_skipped(self):
        """A page that cannot be read must not count as documenting a key, and
        the distribution scan must report it instead of passing it."""
        pdir = self._make_plugin(
            "srv",
            user_config={"API_KEY": {"type": "string"}},
            docs={**self._full_docs(), "setup.md": "Set API_KEY to enable."},
        )
        unreadable = os.path.join(pdir, "setup.md")
        real_open = builtins.open

        def fake_open(path, *args, **kwargs):
            if os.path.normpath(os.fspath(path)) == os.path.normpath(unreadable):
                raise PermissionError(13, "Permission denied", os.fspath(path))
            return real_open(path, *args, **kwargs)

        with mock.patch.object(verify_docs_current, "open", fake_open, create=True):
            code, lines = self._run()

        self.assertEqual(code, 1)
        self.assertTrue(
            any(
                line.startswith("::warning ::plugins")
                and "could not read setup.md" in line
                for line in lines
            ),
            lines,
        )
        self.assertTrue(
            any("userConfig key 'API_KEY'" in line for line in lines), lines
        )
        self.assertTrue(
            any(
                "setup.md: could not verify distribution policy" in line
                for line in lines
            ),
            lines,
        )

    def test_markdown_blob_of_missing_dir_is_empty(self):
        self.assertEqual(verify_docs_current._markdown_blob("plugins/absent"), "")

    def test_plugin_dir_without_manifest_is_skipped(self):
        os.makedirs(os.path.join("plugins", "assets"))
        self._make_plugin("srv", user_config={}, docs=self._full_docs())

        code, lines = self._run()

        self.assertIsNone(code)
        self.assertEqual(
            lines,
            ["All 1 server(s) have current docs (pages + config-param coverage)."],
        )

    def test_unparseable_manifest_is_reported(self):
        pdir = self._make_plugin("srv", user_config={}, docs=self._full_docs())
        with open(
            os.path.join(pdir, ".claude-plugin", "plugin.json"), "w", encoding="utf-8"
        ) as f:
            f.write("{not json")

        code, lines = self._run()

        self.assertEqual(code, 1)
        self.assertTrue(
            any("srv: failed to parse plugin.json" in line for line in lines), lines
        )

    def test_missing_plugins_dir_fails(self):
        os.rmdir("plugins")

        code, lines = self._run()

        self.assertEqual(code, 1)
        self.assertEqual(lines, ["::error ::plugins dir not found: plugins"])

    def test_files_beside_plugin_dirs_are_ignored(self):
        with open(os.path.join("plugins", "README.md"), "w", encoding="utf-8") as f:
            f.write("# Plugins\n")
        self._make_plugin("srv", user_config={}, docs=self._full_docs())

        code, lines = self._run()

        self.assertIsNone(code)
        self.assertIn(
            "All 1 server(s) have current docs (pages + config-param coverage).",
            lines,
        )

    def test_runs_as_a_script(self):
        self._make_plugin("srv", user_config={}, docs=self._full_docs())
        script = os.path.join(
            os.path.dirname(verify_docs_current.__file__), "verify_docs_current.py"
        )
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            runpy.run_path(script, run_name="__main__")
        self.assertIn("All 1 server(s) have current docs", out.getvalue())


if __name__ == "__main__":
    unittest.main()

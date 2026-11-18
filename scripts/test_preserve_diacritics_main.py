#!/usr/bin/env python3
"""Tests for main() of preserve-diacritics.py against a real git index.

pre-commit runs the hook with the staged file names as arguments; run by hand
with no arguments, the hook asks git for the staged files itself. Both paths
run here on a throwaway repository, so the diff parser reads real
``git diff --cached`` output (new-file headers included) instead of a
hand-written string.
"""

import contextlib
import importlib.util
import io
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_SCRIPT = Path(__file__).resolve().parent / "preserve-diacritics.py"


def _load(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_MOD = _load("preserve_diacritics_main")

# Variables that would point a nested git call at another repository, e.g.
# when this suite itself runs inside a git hook.
_GIT_REPO_ENV = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_OBJECT_DIRECTORY")

EM_DASH = "\u2014"


class GitRepoTestCase(unittest.TestCase):
    """A fresh repository in a temp dir, isolated from the user's git config."""

    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)

        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        for key in _GIT_REPO_ENV:
            os.environ.pop(key, None)
        # Global and system config (hooks path, signing, autocrlf) must not
        # change what the fixture commits or how git prints the diff.
        empty_config = os.path.join(self.repo, ".empty-gitconfig")
        Path(empty_config).write_text("", encoding="utf-8")
        os.environ["GIT_CONFIG_GLOBAL"] = empty_config
        os.environ["GIT_CONFIG_NOSYSTEM"] = "1"

        old_cwd = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, old_cwd)

        self._git("init", "-q")
        self._git("config", "user.name", "test")
        self._git("config", "user.email", "test@example.invalid")

    def _git(self, *args: str) -> None:
        subprocess.run(["git", *args], check=True, capture_output=True)

    def _write(self, name: str, text: str) -> None:
        with open(name, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)

    def _commit_base(self, files: dict) -> None:
        for name, text in files.items():
            self._write(name, text)
        self._git("add", "--", *files)
        self._git("commit", "-q", "-m", "base")

    def _stage(self, files: dict) -> None:
        for name, text in files.items():
            self._write(name, text)
        self._git("add", "--", *files)

    def _run_main(self, *args: str) -> tuple[int, str]:
        stderr = io.StringIO()
        with mock.patch.object(sys, "argv", [str(_SCRIPT), *args]):
            with contextlib.redirect_stderr(stderr):
                rc = _MOD.main()
        return rc, stderr.getvalue()


class TestMainOnStagedChanges(GitRepoTestCase):
    def test_staged_rewrite_is_reported_with_file_and_line(self):
        self._commit_base(
            {"docs.md": f"intro\nRust {EM_DASH} the language\n"}
        )
        self._stage(
            {
                "docs.md": "intro\nRust -- the language\n",
                # A brand-new file: its diff starts with --- /dev/null.
                "new.md": f"Added {EM_DASH} new content\n",
            }
        )

        rc, stderr = self._run_main()  # no arguments: ask git

        self.assertEqual(rc, 1)
        self.assertIn("docs.md:2  [unicode-punct", stderr)
        self.assertIn(f"OLD: Rust {EM_DASH} the language", stderr)
        self.assertIn("NEW: Rust -- the language", stderr)
        self.assertIn("Total violations: 1", stderr)
        self.assertNotIn("new.md", stderr)

    def test_clean_change_passes_and_skipped_files_are_not_read(self):
        self._commit_base(
            {
                "docs.md": "plain line\n",
                "uv.lock": f"pkg {EM_DASH} 1.0\n",
            }
        )
        self._stage(
            {
                "docs.md": "plain line, edited\n",
                # The same rewrite that fails a docs page, in a lock file the
                # hook skips by name.
                "uv.lock": "pkg -- 1.0\n",
            }
        )

        rc, stderr = self._run_main("docs.md", "uv.lock", "missing.md")

        self.assertEqual(rc, 0)
        self.assertEqual(stderr, "")

    def test_report_lists_twenty_violations_then_a_count(self):
        count = 25
        self._commit_base(
            {"list.md": "".join(f"item {EM_DASH} {i}\n" for i in range(count))}
        )
        self._stage({"list.md": "".join(f"item -- {i}\n" for i in range(count))})

        rc, stderr = self._run_main("list.md")

        self.assertEqual(rc, 1)
        self.assertEqual(stderr.count("[unicode-punct"), 20)
        self.assertIn("... and 5 more", stderr)
        self.assertIn(f"Total violations: {count}", stderr)

    def test_runs_as_a_script(self):
        self._commit_base({"docs.md": "plain line\n"})
        with mock.patch.object(sys, "argv", [str(_SCRIPT)]):
            with self.assertRaises(SystemExit) as cm:
                runpy.run_path(str(_SCRIPT), run_name="__main__")
        self.assertEqual(cm.exception.code, 0)


class TestModuleLoad(unittest.TestCase):
    def test_loads_when_stderr_cannot_be_reconfigured(self):
        # A replaced stderr (a test runner's capture, a plain StringIO) has no
        # reconfigure(); loading the hook must not depend on it.
        replacement = io.StringIO()
        with mock.patch.object(sys, "stderr", replacement):
            module = _load("preserve_diacritics_plain_stderr")
            self.assertIs(sys.stderr, replacement)
        self.assertEqual(module._check_pair("same", "same"), [])


if __name__ == "__main__":
    unittest.main()

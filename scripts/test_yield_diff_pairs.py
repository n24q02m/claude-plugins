#!/usr/bin/env python3
"""Tests for _yield_diff_pairs in preserve-diacritics.py."""

import unittest
from unittest.mock import patch
import importlib.util
from pathlib import Path
import subprocess

_HERE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location(
    "preserve_diacritics", _HERE / "preserve-diacritics.py"
)
assert _SPEC is not None and _SPEC.loader is not None
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

yield_diff_pairs = _MOD._yield_diff_pairs


class TestYieldDiffPairs(unittest.TestCase):
    def test_empty_files(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            results = list(yield_diff_pairs([]))
            self.assertEqual(results, [])
            mock_git.assert_not_called()

    def test_single_change(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            mock_git.return_value = (
                "diff --git file1.txt file1.txt\n"
                "--- file1.txt\n"
                "+++ file1.txt\n"
                "@@ -1 +1 @@\n"
                "-old line\n"
                "+new line\n"
            )
            results = list(yield_diff_pairs(["file1.txt"]))
            self.assertEqual(results, [("file1.txt", 1, "old line", "new line")])

    def test_multiple_changes_in_hunk(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            mock_git.return_value = (
                "diff --git file1.txt file1.txt\n"
                "--- file1.txt\n"
                "+++ file1.txt\n"
                "@@ -1,2 +1,2 @@\n"
                "-old1\n"
                "-old2\n"
                "+new1\n"
                "+new2\n"
            )
            results = list(yield_diff_pairs(["file1.txt"]))
            self.assertEqual(
                results,
                [
                    ("file1.txt", 1, "old1", "new1"),
                    ("file1.txt", 2, "old2", "new2"),
                ],
            )

    def test_multiple_hunks(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            mock_git.return_value = (
                "diff --git file1.txt file1.txt\n"
                "--- file1.txt\n"
                "+++ file1.txt\n"
                "@@ -1 +1 @@\n"
                "-old1\n"
                "+new1\n"
                "@@ -10 +10 @@\n"
                "-old2\n"
                "+new2\n"
            )
            results = list(yield_diff_pairs(["file1.txt"]))
            self.assertEqual(
                results,
                [
                    ("file1.txt", 1, "old1", "new1"),
                    ("file1.txt", 10, "old2", "new2"),
                ],
            )

    def test_multiple_files(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            mock_git.return_value = (
                "diff --git file1.txt file1.txt\n"
                "--- file1.txt\n"
                "+++ file1.txt\n"
                "@@ -1 +1 @@\n"
                "-f1-old\n"
                "+f1-new\n"
                "diff --git file2.txt file2.txt\n"
                "--- file2.txt\n"
                "+++ file2.txt\n"
                "@@ -5 +5 @@\n"
                "-f2-old\n"
                "+f2-new\n"
            )
            results = list(yield_diff_pairs(["file1.txt", "file2.txt"]))
            self.assertEqual(
                results,
                [
                    ("file1.txt", 1, "f1-old", "f1-new"),
                    ("file2.txt", 5, "f2-old", "f2-new"),
                ],
            )

    def test_unbalanced_changes(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            # More removals than additions
            mock_git.return_value = (
                "diff --git file1.txt file1.txt\n"
                "--- file1.txt\n"
                "+++ file1.txt\n"
                "@@ -1,3 +1 @@\n"
                "-rem1\n"
                "-rem2\n"
                "-rem3\n"
                "+add1\n"
            )
            results = list(yield_diff_pairs(["file1.txt"]))
            # Should only yield pairs for min(rem, add)
            self.assertEqual(results, [("file1.txt", 1, "rem1", "add1")])

    def test_context_lines(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            mock_git.return_value = (
                "diff --git file1.txt file1.txt\n"
                "--- file1.txt\n"
                "+++ file1.txt\n"
                "@@ -1,5 +1,5 @@\n"
                " context1\n"
                "-old1\n"
                "+new1\n"
                " context2\n"
                "-old2\n"
                "+new2\n"
            )
            results = list(yield_diff_pairs(["file1.txt"]))
            self.assertEqual(
                results,
                [
                    ("file1.txt", 2, "old1", "new1"),
                    ("file1.txt", 4, "old2", "new2"),
                ],
            )

    def test_batching(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            # Batch size is 50. Test with 60 files.
            files = [f"file{i}.txt" for i in range(60)]
            mock_git.return_value = ""  # No diffs for simplicity
            list(yield_diff_pairs(files))
            self.assertEqual(mock_git.call_count, 2)

    def test_git_error_continues(self):
        with patch.object(_MOD, "_run_git") as mock_git:
            # First batch fails, second succeeds.
            files = [f"file{i}.txt" for i in range(60)]

            def side_effect(args, pathspecs=None):
                if "file0.txt" in pathspecs:
                    raise subprocess.CalledProcessError(1, "git diff")
                return (
                    "diff --git file55.txt file55.txt\n"
                    "--- file55.txt\n"
                    "+++ file55.txt\n"
                    "@@ -1 +1 @@\n"
                    "-old\n"
                    "+new\n"
                )

            mock_git.side_effect = side_effect
            results = list(yield_diff_pairs(files))
            self.assertEqual(results, [("file55.txt", 1, "old", "new")])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
import unittest
from unittest.mock import patch, MagicMock
import importlib.util
from pathlib import Path
import subprocess

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "preserve_diacritics", _PROJECT_ROOT / "scripts" / "preserve-diacritics.py"
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

class TestRunGit(unittest.TestCase):
    @patch("subprocess.run")
    def test_run_git_with_pathspecs(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = b"some output"
        mock_run.return_value = mock_result

        args = ["diff", "--cached"]
        pathspecs = ["file1.txt", "file2.txt"]

        _MOD._run_git(args, pathspecs=pathspecs)

        expected_cmd = ["git", "diff", "--cached", "--", "file1.txt", "file2.txt"]
        mock_run.assert_called_once()
        actual_cmd = mock_run.call_args[0][0]
        self.assertEqual(actual_cmd, expected_cmd)

    @patch("subprocess.run")
    def test_run_git_without_pathspecs(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = b"some output"
        mock_run.return_value = mock_result

        args = ["status"]

        _MOD._run_git(args)

        expected_cmd = ["git", "status"]
        mock_run.assert_called_once()
        actual_cmd = mock_run.call_args[0][0]
        self.assertEqual(actual_cmd, expected_cmd)

    @patch("subprocess.run")
    def test_run_git_option_injection_prevention(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = b"some output"
        mock_run.return_value = mock_result

        args = ["diff"]
        # Malicious pathspec that looks like an option
        pathspecs = ["--version"]

        _MOD._run_git(args, pathspecs=pathspecs)

        # Should be git diff -- --version
        expected_cmd = ["git", "diff", "--", "--version"]
        mock_run.assert_called_once()
        actual_cmd = mock_run.call_args[0][0]
        self.assertEqual(actual_cmd, expected_cmd)

if __name__ == "__main__":
    unittest.main()

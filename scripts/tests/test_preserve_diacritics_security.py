import unittest
from unittest.mock import patch, MagicMock
import importlib.util
from pathlib import Path
import os
import sys

# Import the module under test
_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
_SPEC = importlib.util.spec_from_file_location(
    "preserve_diacritics", _SCRIPTS / "preserve-diacritics.py"
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)


class TestPreserveDiacriticsSecurity(unittest.TestCase):
    @patch("subprocess.run")
    def test_run_git_no_pathspecs(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = b"some output"
        mock_run.return_value = mock_result

        _MOD._run_git(["diff", "--name-only"])

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ["git", "diff", "--name-only"])

    @patch("subprocess.run")
    def test_run_git_with_pathspecs(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = b"some output"
        mock_run.return_value = mock_result

        _MOD._run_git(["diff"], pathspecs=["file1.txt", "file2.txt"])

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd, ["git", "diff", "--", "file1.txt", "file2.txt"])

    def test_run_git_pathspecs_is_keyword_only(self):
        with self.assertRaises(TypeError):
            # Attempt to pass pathspecs as a positional argument
            _MOD._run_git(["diff"], ["file1.txt"])


if __name__ == "__main__":
    unittest.main()

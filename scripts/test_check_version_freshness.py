#!/usr/bin/env python3
"""Unit tests for check_version_freshness script."""

import unittest
import os
import json
import shutil
import tempfile
import subprocess
from unittest.mock import patch, MagicMock, mock_open
import check_version_freshness

class TestCheckVersionFreshness(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def create_plugin_json(self, path, version):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump({"version": version}, f)

    @patch('subprocess.run')
    def test_check_plugin_up_to_date(self, mock_run):
        """Test plugin is up-to-date."""
        plugin = {"name": "test-plugin", "source": "./plugins/test-plugin"}
        self.create_plugin_json("plugins/test-plugin/.claude-plugin/plugin.json", "1.0.0")

        mock_run.return_value = MagicMock(returncode=0, stdout="v1.0.0\n")

        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "up-to-date")
        self.assertEqual(result["marketplace_ver"], "1.0.0")

    @patch('subprocess.run')
    def test_check_plugin_stale(self, mock_run):
        """Test plugin is stale."""
        plugin = {"name": "test-plugin", "source": "./plugins/test-plugin"}
        self.create_plugin_json("plugins/test-plugin/.claude-plugin/plugin.json", "1.0.0")

        mock_run.return_value = MagicMock(returncode=0, stdout="v1.1.0\n")

        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["marketplace_ver"], "1.0.0")
        self.assertEqual(result["latest_tag"], "1.1.0")

    @patch('subprocess.run')
    def test_check_plugin_no_release(self, mock_run):
        """Test plugin has no release."""
        plugin = {"name": "test-plugin", "source": "./plugins/test-plugin"}
        self.create_plugin_json("plugins/test-plugin/.claude-plugin/plugin.json", "1.0.0")

        mock_run.return_value = MagicMock(returncode=1)

        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "no-release")

    @patch('subprocess.run')
    def test_check_plugin_timeout(self, mock_run):
        """Test gh command timeout."""
        plugin = {"name": "test-plugin", "source": "./plugins/test-plugin"}
        self.create_plugin_json("plugins/test-plugin/.claude-plugin/plugin.json", "1.0.0")

        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["gh"], timeout=30)

        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "timeout")

    @patch('subprocess.run')
    def test_check_plugin_error(self, mock_run):
        """Test generic error during check."""
        plugin = {"name": "test-plugin", "source": "./plugins/test-plugin"}
        self.create_plugin_json("plugins/test-plugin/.claude-plugin/plugin.json", "1.0.0")

        mock_run.side_effect = Exception("GH failure")

        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "GH failure")

    def test_check_plugin_invalid_name(self):
        """Test plugin with invalid name."""
        plugin = {"name": "invalid name!", "source": "./plugins/invalid"}
        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid name format")

    @patch('subprocess.run')
    def test_check_plugin_fallback_gemini(self, mock_run):
        """Test fallback to gemini-extension.json."""
        plugin = {"name": "test-plugin", "source": "./plugins/test-plugin"}
        # No .claude-plugin/plugin.json
        self.create_plugin_json("plugins/test-plugin/gemini-extension.json", "0.9.0")

        mock_run.return_value = MagicMock(returncode=0, stdout="0.9.0\n")

        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "up-to-date")
        self.assertEqual(result["marketplace_ver"], "0.9.0")

    @patch('check_version_freshness.check_plugin')
    @patch('builtins.open', new_callable=mock_open, read_data='{"plugins": [{"name": "p1", "source": "s1"}]}')
    def test_check_version_freshness_stale(self, mock_file, mock_check):
        """Test orchestration with a stale plugin."""
        mock_check.return_value = {
            "status": "stale",
            "name": "p1",
            "marketplace_ver": "1.0.0",
            "latest_tag": "1.1.0"
        }

        with patch('sys.stdout', new=MagicMock()) as mock_stdout:
            check_version_freshness.check_version_freshness()
            # Verify warning was printed
            output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("::warning ::p1 is stale", output)
            self.assertIn("1 plugin(s) need sync", output)

    @patch('check_version_freshness.check_plugin')
    @patch('builtins.open', new_callable=mock_open, read_data='{"plugins": [{"name": "p1", "source": "s1"}]}')
    def test_check_version_freshness_up_to_date(self, mock_file, mock_check):
        """Test orchestration with an up-to-date plugin."""
        mock_check.return_value = {
            "status": "up-to-date",
            "name": "p1",
            "marketplace_ver": "1.0.0"
        }

        with patch('sys.stdout', new=MagicMock()) as mock_stdout:
            check_version_freshness.check_version_freshness()
            output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("All plugins up-to-date", output)

    @patch('check_version_freshness.check_plugin')
    @patch('builtins.open', new_callable=mock_open, read_data='{"plugins": [{"name": "p1", "source": "s1"}]}')
    def test_check_version_freshness_error(self, mock_file, mock_check):
        """Test orchestration with an error status."""
        mock_check.return_value = {
            "status": "error",
            "name": "p1",
            "marketplace_ver": "unknown",
            "error": "some error"
        }

        with patch('sys.stdout', new=MagicMock()) as mock_stdout:
            check_version_freshness.check_version_freshness()
            output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            self.assertIn("::error ::p1 error: some error", output)

if __name__ == '__main__':
    unittest.main()

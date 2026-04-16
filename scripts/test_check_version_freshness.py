import unittest
from unittest.mock import patch, MagicMock
import subprocess
import os
import check_version_freshness

class TestCheckVersionFreshness(unittest.TestCase):

    @patch('check_version_freshness.subprocess.run')
    @patch('check_version_freshness.os.path.exists')
    @patch('check_version_freshness.open', create=True)
    def test_check_plugin_valid_name(self, mock_open, mock_exists, mock_run):
        # Setup
        plugin = {"name": "valid-plugin-123", "source": "./plugins/valid-plugin-123"}
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '{"version": "1.0.0"}'

        # Mocking json.load because we are mocking open
        with patch('json.load', return_value={"version": "1.0.0"}):
            mock_run.return_value = MagicMock(returncode=0, stdout="v1.0.0\n")

            result = check_version_freshness.check_plugin(plugin)

            self.assertEqual(result["status"], "up-to-date")
            mock_run.assert_called_once()
            # Verify the repo argument
            args, kwargs = mock_run.call_args
            repo_arg = args[0][4]
            self.assertEqual(repo_arg, "n24q02m/valid-plugin-123")

    @patch('check_version_freshness.subprocess.run')
    def test_check_plugin_invalid_name_injection(self, mock_run):
        # Injection attempt
        plugin = {"name": "invalid; rm -rf /", "source": "./plugins/invalid"}

        result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid name format")
        mock_run.assert_not_called()

    @patch('check_version_freshness.subprocess.run')
    def test_check_plugin_invalid_name_space(self, mock_run):
        plugin = {"name": "plugin name", "source": "./plugins/plugin"}

        result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid name format")
        mock_run.assert_not_called()

    @patch('check_version_freshness.subprocess.run')
    def test_check_plugin_name_with_underscore(self, mock_run):
        # Now FORBIDDEN by ^[a-zA-Z0-9-]+$
        plugin = {"name": "plugin_with_underscore", "source": "./plugins/plugin"}

        result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid name format")
        mock_run.assert_not_called()

    @patch('check_version_freshness.subprocess.run')
    def test_check_plugin_name_with_newline(self, mock_run):
        plugin = {"name": "plugin-name\n", "source": "./plugins/plugin"}

        result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid name format")
        mock_run.assert_not_called()

    @patch('check_version_freshness.subprocess.run')
    @patch('check_version_freshness.os.path.exists')
    @patch('check_version_freshness.open', create=True)
    def test_check_plugin_stale(self, mock_open, mock_exists, mock_run):
        plugin = {"name": "stale-plugin", "source": "./plugins/stale-plugin"}
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '{"version": "1.0.0"}'

        with patch('json.load', return_value={"version": "1.0.0"}):
            mock_run.return_value = MagicMock(returncode=0, stdout="v1.1.0\n")

            result = check_version_freshness.check_plugin(plugin)

            self.assertEqual(result["status"], "stale")
            self.assertEqual(result["marketplace_ver"], "1.0.0")
            self.assertEqual(result["latest_tag"], "1.1.0")

    @patch('check_version_freshness.subprocess.run')
    @patch('check_version_freshness.os.path.exists')
    @patch('check_version_freshness.open', create=True)
    def test_check_plugin_no_release(self, mock_open, mock_exists, mock_run):
        plugin = {"name": "no-release-plugin", "source": "./plugins/no-release-plugin"}
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '{"version": "1.0.0"}'

        with patch('json.load', return_value={"version": "1.0.0"}):
            mock_run.return_value = MagicMock(returncode=1)

            result = check_version_freshness.check_plugin(plugin)

            self.assertEqual(result["status"], "no-release")

    @patch('check_version_freshness.subprocess.run')
    @patch('check_version_freshness.os.path.exists')
    @patch('check_version_freshness.open', create=True)
    def test_check_plugin_timeout(self, mock_open, mock_exists, mock_run):
        plugin = {"name": "timeout-plugin", "source": "./plugins/timeout-plugin"}
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '{"version": "1.0.0"}'

        with patch('json.load', return_value={"version": "1.0.0"}):
            mock_run.side_effect = subprocess.TimeoutExpired(cmd=["gh", "release", "view"], timeout=30)

            result = check_version_freshness.check_plugin(plugin)

            self.assertEqual(result["status"], "timeout")

    @patch('check_version_freshness.subprocess.run')
    @patch('check_version_freshness.os.path.exists')
    @patch('check_version_freshness.open', create=True)
    def test_check_plugin_gemini_fallback(self, mock_open, mock_exists, mock_run):
        plugin = {"name": "gemini-plugin", "source": "./plugins/gemini-plugin"}

        # First path (.claude-plugin/plugin.json) doesn't exist, second (gemini-extension.json) does
        mock_exists.side_effect = lambda path: "gemini-extension.json" in path
        mock_open.return_value.__enter__.return_value.read.return_value = '{"version": "2.0.0"}'

        with patch('json.load', return_value={"version": "2.0.0"}):
            mock_run.return_value = MagicMock(returncode=0, stdout="v2.0.0\n")

            result = check_version_freshness.check_plugin(plugin)

            self.assertEqual(result["status"], "up-to-date")
            self.assertEqual(result["marketplace_ver"], "2.0.0")

if __name__ == '__main__':
    unittest.main()

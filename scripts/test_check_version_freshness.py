import unittest
from unittest.mock import patch, MagicMock
import os
import check_version_freshness
import json
import urllib.request
import urllib.error

class TestCheckVersionFreshness(unittest.TestCase):

    def setUp(self):
        # Clear cache before each test
        check_version_freshness._cache = {}

    @patch('check_version_freshness.urllib.request.urlopen')
    @patch('check_version_freshness.os.path.exists')
    @patch('check_version_freshness.open', create=True)
    def test_check_plugin_valid_name(self, mock_open, mock_exists, mock_urlopen):
        # Setup
        plugin = {"name": "valid-plugin-123", "source": "./plugins/valid-plugin-123"}
        mock_exists.return_value = True

        # Mocking json.load because we are mocking open
        with patch('json.load', return_value={"version": "1.0.0"}):
            # Mock API response
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"tag_name": "v1.0.0"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            result = check_version_freshness.check_plugin(plugin)

            self.assertEqual(result["status"], "up-to-date")
            mock_urlopen.assert_called_once()

            # Verify the URL
            args, _ = mock_urlopen.call_args
            req = args[0]
            self.assertEqual(req.full_url, "https://api.github.com/repos/n24q02m/valid-plugin-123/releases/latest")

    @patch('check_version_freshness.urllib.request.urlopen')
    def test_check_plugin_invalid_name_injection(self, mock_urlopen):
        # Injection attempt
        plugin = {"name": "invalid; rm -rf /", "source": "./plugins/invalid"}

        result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid name format")
        mock_urlopen.assert_not_called()

    @patch('check_version_freshness.urllib.request.urlopen')
    def test_check_plugin_cache(self, mock_urlopen):
        plugin = {"name": "cached-plugin", "source": "./plugins/cached-plugin"}

        # Mock API response
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.2.3"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        # First call
        with patch('check_version_freshness.os.path.exists', return_value=False):
            check_version_freshness.check_plugin(plugin)
            # Second call
            check_version_freshness.check_plugin(plugin)

        # urllib.request.urlopen should only be called once due to caching
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch('check_version_freshness.urllib.request.urlopen')
    def test_check_plugin_stale(self, mock_urlopen):
        plugin = {"name": "stale-plugin", "source": "./plugins/stale-plugin"}

        # Mock marketplace version (1.0.0)
        with patch('check_version_freshness.os.path.exists', return_value=True), \
             patch('check_version_freshness.open', create=True), \
             patch('json.load', return_value={"version": "1.0.0"}):

            # Mock API response (1.1.0)
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"tag_name": "v1.1.0"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            result = check_version_freshness.check_plugin(plugin)

            self.assertEqual(result["status"], "stale")
            self.assertEqual(result["marketplace_ver"], "1.0.0")
            self.assertEqual(result["latest_tag"], "1.1.0")

    @patch('check_version_freshness.urllib.request.urlopen')
    @patch('check_version_freshness.os.path.exists', return_value=False)
    def test_check_plugin_uses_snake_case_tag_name(self, mock_exists, mock_urlopen):
        plugin = {"name": "snake-case-plugin", "source": "./plugins/snake-case-plugin"}

        # Mock API response with BOTH tag_name and tagName (to ensure it picks tag_name)
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v2.0.0", "tagName": "v1.0.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = check_version_freshness.check_plugin(plugin)

        # Should pick up 2.0.0 from tag_name
        self.assertEqual(result["latest_tag"], "2.0.0")

    @patch('check_version_freshness.urllib.request.urlopen')
    @patch('check_version_freshness.os.path.exists', return_value=False)
    def test_check_plugin_timeout(self, mock_exists, mock_urlopen):
        plugin = {"name": "timeout-plugin", "source": "./plugins/timeout-plugin"}

        # Mock timeout
        mock_urlopen.side_effect = urllib.error.URLError("timed out")

        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "timeout")

    @patch('check_version_freshness.urllib.request.urlopen')
    @patch('check_version_freshness.os.path.exists', return_value=False)
    def test_check_plugin_404(self, mock_exists, mock_urlopen):
        plugin = {"name": "no-release-plugin", "source": "./plugins/no-release-plugin"}

        # Mock 404
        mock_error = urllib.error.HTTPError(None, 404, "Not Found", None, None)
        mock_urlopen.side_effect = mock_error

        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "no-release")

    @patch('check_version_freshness.urllib.request.urlopen')
    @patch('check_version_freshness.os.path.exists', return_value=False)
    def test_check_plugin_auth_header(self, mock_exists, mock_urlopen):
        plugin = {"name": "auth-plugin", "source": "./plugins/auth-plugin"}

        with patch.dict(os.environ, {"GITHUB_TOKEN": "secret-token"}):
            # Mock API response
            mock_response = MagicMock()
            mock_response.read.return_value = b'{"tag_name": "v1.0.0"}'
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response

            check_version_freshness.check_plugin(plugin)

            args, _ = mock_urlopen.call_args
            req = args[0]
            self.assertEqual(req.get_header("Authorization"), "token secret-token")

if __name__ == '__main__':
    unittest.main()

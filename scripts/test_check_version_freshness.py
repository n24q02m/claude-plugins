import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

import check_version_freshness


class TestCheckVersionFreshness(unittest.TestCase):
    def setUp(self):
        # Clear cache before each test
        check_version_freshness._cache = {}

    # ------------------------------------------------------------------
    # Happy path + URL construction
    # ------------------------------------------------------------------

    @patch("check_version_freshness.urllib.request.urlopen")
    @patch("check_version_freshness.os.path.exists")
    def test_check_plugin_valid_name(self, mock_exists, mock_urlopen):
        plugin = {"name": "valid-plugin-123", "source": "./plugins/valid-plugin-123"}
        mock_exists.return_value = True

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.0.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "up-to-date")
        mock_urlopen.assert_called_once()
        args, _ = mock_urlopen.call_args
        req = args[0]
        self.assertEqual(
            req.full_url,
            "https://api.github.com/repos/n24q02m/valid-plugin-123/releases/latest",
        )

    # ------------------------------------------------------------------
    # Input validation (no network)
    # ------------------------------------------------------------------

    @patch("check_version_freshness.urllib.request.urlopen")
    def test_check_plugin_invalid_name_injection(self, mock_urlopen):
        plugin = {"name": "invalid; rm -rf /", "source": "./plugins/invalid"}
        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid name format")
        mock_urlopen.assert_not_called()

    @patch("check_version_freshness.urllib.request.urlopen")
    def test_check_plugin_invalid_name_space(self, mock_urlopen):
        plugin = {"name": "plugin name", "source": "./plugins/plugin"}
        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "error")
        mock_urlopen.assert_not_called()

    @patch("check_version_freshness.urllib.request.urlopen")
    def test_check_plugin_invalid_name_underscore(self, mock_urlopen):
        plugin = {"name": "plugin_with_underscore", "source": "./plugins/p"}
        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "error")
        mock_urlopen.assert_not_called()

    @patch("check_version_freshness.urllib.request.urlopen")
    def test_check_plugin_invalid_name_newline(self, mock_urlopen):
        plugin = {"name": "plugin-name\n", "source": "./plugins/p"}
        result = check_version_freshness.check_plugin(plugin)
        self.assertEqual(result["status"], "error")
        mock_urlopen.assert_not_called()

    # ------------------------------------------------------------------
    # Status transitions: stale / no-release / timeout / error
    # ------------------------------------------------------------------

    @patch("check_version_freshness.urllib.request.urlopen")
    @patch("check_version_freshness.os.path.exists", return_value=True)
    def test_check_plugin_stale(self, _mock_exists, mock_urlopen):
        plugin = {"name": "stale-plugin", "source": "./plugins/stale-plugin"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.1.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["marketplace_ver"], "1.0.0")
        self.assertEqual(result["latest_tag"], "1.1.0")

    @patch("check_version_freshness.urllib.request.urlopen")
    @patch("check_version_freshness.os.path.exists", return_value=True)
    def test_check_plugin_no_release_404(self, _mock_exists, mock_urlopen):
        plugin = {
            "name": "no-release-plugin",
            "source": "./plugins/no-release-plugin",
        }
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="x", code=404, msg="Not Found", hdrs=None, fp=None
        )

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "no-release")

    @patch("check_version_freshness.urllib.request.urlopen")
    @patch("check_version_freshness.os.path.exists", return_value=True)
    def test_check_plugin_timeout(self, _mock_exists, mock_urlopen):
        plugin = {"name": "timeout-plugin", "source": "./plugins/timeout-plugin"}
        mock_urlopen.side_effect = urllib.error.URLError(reason=TimeoutError())

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "timeout")

    @patch("check_version_freshness.urllib.request.urlopen")
    @patch("check_version_freshness.os.path.exists", return_value=True)
    def test_check_plugin_error_generic(self, _mock_exists, mock_urlopen):
        plugin = {"name": "error-plugin", "source": "./plugins/error-plugin"}
        mock_urlopen.side_effect = urllib.error.URLError(reason="boom")

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "error")

    # ------------------------------------------------------------------
    # Fallback: gemini-extension.json
    # ------------------------------------------------------------------

    @patch("check_version_freshness.urllib.request.urlopen")
    @patch("check_version_freshness.os.path.exists")
    def test_check_plugin_gemini_fallback(self, mock_exists, mock_urlopen):
        plugin = {"name": "gemini-plugin", "source": "./plugins/gemini-plugin"}
        mock_exists.side_effect = lambda path: "gemini-extension.json" in path

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v2.0.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "2.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "up-to-date")
        self.assertEqual(result["marketplace_ver"], "2.0.0")

    # ------------------------------------------------------------------
    # Caching: repeated lookups for same repo reuse cached result
    # ------------------------------------------------------------------

    @patch("check_version_freshness.urllib.request.urlopen")
    def test_check_plugin_cache(self, mock_urlopen):
        plugin = {"name": "cached-plugin", "source": "./plugins/cached-plugin"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.2.3"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with patch("check_version_freshness.os.path.exists", return_value=False):
            check_version_freshness.check_plugin(plugin)
            check_version_freshness.check_plugin(plugin)

        self.assertEqual(mock_urlopen.call_count, 1)

    # ------------------------------------------------------------------
    # Authentication header: GITHUB_TOKEN is attached when set
    # ------------------------------------------------------------------

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=False)
    @patch("check_version_freshness.urllib.request.urlopen")
    @patch("check_version_freshness.os.path.exists", return_value=True)
    def test_check_plugin_uses_auth_header(
        self, _mock_exists, mock_urlopen
    ):
        plugin = {"name": "auth-plugin", "source": "./plugins/auth-plugin"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.0.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            check_version_freshness.check_plugin(plugin)

        args, _ = mock_urlopen.call_args
        req = args[0]
        # urllib lowercases header names internally
        self.assertEqual(req.headers.get("Authorization"), "token secret-token")

    # ------------------------------------------------------------------
    # Regression: GitHub REST API returns snake_case tag_name, not camelCase
    # ------------------------------------------------------------------

    @patch("check_version_freshness.urllib.request.urlopen")
    @patch("check_version_freshness.os.path.exists", return_value=True)
    def test_check_plugin_uses_snake_case_tag_name(
        self, _mock_exists, mock_urlopen
    ):
        """API payload uses tag_name; tagName (camelCase) would regress to empty tag."""
        plugin = {"name": "regression-plugin", "source": "./plugins/regression-plugin"}

        mock_response = MagicMock()
        # Payload includes BOTH keys; only tag_name should be read.
        mock_response.read.return_value = json.dumps(
            {"tag_name": "v3.4.5", "tagName": "v9.9.9"}
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "3.4.5"}),
        ):
            result = check_version_freshness.check_plugin(plugin)

        self.assertEqual(result["status"], "up-to-date")
        self.assertEqual(result["marketplace_ver"], "3.4.5")


if __name__ == "__main__":
    unittest.main()

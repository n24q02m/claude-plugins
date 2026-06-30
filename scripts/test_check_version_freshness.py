import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

import check_version_freshness


class TestCheckVersionFreshness(unittest.TestCase):
    def setUp(self):
        # Clear cache before each test
        check_version_freshness._latest_tag_cache.clear()

    # ------------------------------------------------------------------
    # Happy path + URL construction
    # ------------------------------------------------------------------

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_valid_name(self, mock_urlopen):
        plugin = {"name": "valid-plugin-123", "source": "./plugins/valid-plugin-123"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.0.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin, "n24q02m")

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

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_invalid_name_injection(self, mock_urlopen):
        plugin = {"name": "invalid; rm -rf /", "source": "./plugins/invalid"}
        result = check_version_freshness.check_plugin(plugin, "n24q02m")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "invalid name format")

    def test_check_plugin_path_traversal(self):
        plugin = {"name": "test-plugin", "source": "../../../etc/passwd"}
        res = check_version_freshness.check_plugin(plugin, "n24q02m")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error"], "invalid source path")

    @patch("os.path.realpath")
    @patch("os.getcwd")
    def test_check_plugin_symlink_traversal(self, mock_getcwd, mock_realpath):
        mock_getcwd.return_value = "/app"
        # First call for abs_base, second for abs_target
        mock_realpath.side_effect = ["/app", "/etc/passwd"]
        plugin = {"name": "test-plugin", "source": "plugins/malicious"}
        res = check_version_freshness.check_plugin(plugin, "n24q02m")
        self.assertEqual(res["status"], "error")
        self.assertEqual(res["error"], "invalid source path")

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_invalid_name_space(self, mock_urlopen):
        plugin = {"name": "plugin name", "source": "./plugins/plugin"}
        result = check_version_freshness.check_plugin(plugin, "n24q02m")
        self.assertEqual(result["status"], "error")
        mock_urlopen.assert_not_called()

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_invalid_name_underscore(self, mock_urlopen):
        plugin = {"name": "plugin_with_underscore", "source": "./plugins/p"}
        result = check_version_freshness.check_plugin(plugin, "n24q02m")
        self.assertEqual(result["status"], "error")
        mock_urlopen.assert_not_called()

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_invalid_name_newline(self, mock_urlopen):
        plugin = {"name": "plugin-name\n", "source": "./plugins/p"}
        result = check_version_freshness.check_plugin(plugin, "n24q02m")
        self.assertEqual(result["status"], "error")
        mock_urlopen.assert_not_called()

    # ------------------------------------------------------------------
    # Status transitions: stale / no-release / timeout / error
    # ------------------------------------------------------------------

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_stale(self, mock_urlopen):
        plugin = {"name": "stale-plugin", "source": "./plugins/stale-plugin"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.1.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin, "n24q02m")

        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["marketplace_ver"], "1.0.0")
        self.assertEqual(result["latest_tag"], "1.1.0")

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_no_release_404(self, mock_urlopen):
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
            result = check_version_freshness.check_plugin(plugin, "n24q02m")

        self.assertEqual(result["status"], "no-release")

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_timeout(self, mock_urlopen):
        plugin = {"name": "timeout-plugin", "source": "./plugins/timeout-plugin"}
        mock_urlopen.side_effect = urllib.error.URLError(reason=TimeoutError())

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin, "n24q02m")

        self.assertEqual(result["status"], "timeout")

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_error_generic(self, mock_urlopen):
        plugin = {"name": "error-plugin", "source": "./plugins/error-plugin"}
        mock_urlopen.side_effect = urllib.error.URLError(reason="boom")

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin, "n24q02m")

        self.assertEqual(result["status"], "error")

    # ------------------------------------------------------------------
    # Fallback: gemini-extension.json
    # ------------------------------------------------------------------

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_gemini_fallback(self, mock_urlopen):
        plugin = {"name": "gemini-plugin", "source": "./plugins/gemini-plugin"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v2.0.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        def mock_open_fallback(path, *args, **kwargs):
            if "plugin.json" in path:
                raise FileNotFoundError()
            return MagicMock()

        with (
            patch(
                "check_version_freshness.open",
                create=True,
                side_effect=mock_open_fallback,
            ),
            patch("json.load", return_value={"version": "2.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin, "n24q02m")

        self.assertEqual(result["status"], "up-to-date")
        self.assertEqual(result["marketplace_ver"], "2.0.0")

    # ------------------------------------------------------------------
    # Caching: repeated lookups for same repo reuse cached result
    # ------------------------------------------------------------------

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_cache(self, mock_urlopen):
        plugin = {"name": "cached-plugin", "source": "./plugins/cached-plugin"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.2.3"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with patch(
            "check_version_freshness.open", create=True, side_effect=FileNotFoundError
        ):
            check_version_freshness.check_plugin(plugin, "n24q02m")
            check_version_freshness.check_plugin(plugin, "n24q02m")

        self.assertEqual(mock_urlopen.call_count, 1)

    # ------------------------------------------------------------------
    # Authentication header: GITHUB_TOKEN is attached when set
    # ------------------------------------------------------------------

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=False)
    @patch("check_version_freshness._opener.open")
    def test_check_plugin_uses_auth_header(self, mock_urlopen):
        plugin = {"name": "auth-plugin", "source": "./plugins/auth-plugin"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.0.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("check_version_freshness.open", create=True),
            patch("json.load", return_value={"version": "1.0.0"}),
        ):
            check_version_freshness.check_plugin(plugin, "n24q02m")

        args, _ = mock_urlopen.call_args
        req = args[0]
        # urllib lowercases header names internally
        self.assertEqual(req.headers.get("Authorization"), "token secret-token")

    # ------------------------------------------------------------------
    # SSRF Mitigation: NoAuthRedirectHandler
    # ------------------------------------------------------------------

    def test_no_auth_redirect_handler_cross_origin(self):
        """Should strip Authorization header when redirecting to a different origin."""
        req = urllib.request.Request(
            "https://api.github.com/test",
            headers={"Authorization": "token secret", "Cookie": "session=123"},
        )
        req.add_unredirected_header("Authorization", "token unredirected")
        req.add_unredirected_header("Cookie", "session=456")
        handler = check_version_freshness.NoAuthRedirectHandler()
        # Mock the underlying redirect_request to just return a Request object
        # with the new URL and the old headers.
        with patch("urllib.request.HTTPRedirectHandler.redirect_request") as mock_super:
            mock_req = urllib.request.Request(
                "https://raw.githubusercontent.com/test",
                headers=req.headers,
            )
            mock_req.unredirected_hdrs = req.unredirected_hdrs.copy()
            mock_super.return_value = mock_req
            redirected_req = handler.redirect_request(
                req,
                MagicMock(),
                302,
                "Found",
                MagicMock(),
                "https://raw.githubusercontent.com/test",
            )
            self.assertNotIn("Authorization", redirected_req.headers)
            self.assertNotIn("Cookie", redirected_req.headers)
            self.assertNotIn("authorization", redirected_req.headers)
            self.assertNotIn("Authorization", redirected_req.unredirected_hdrs)
            self.assertNotIn("Cookie", redirected_req.unredirected_hdrs)
            self.assertNotIn("authorization", redirected_req.unredirected_hdrs)
            self.assertNotIn("cookie", redirected_req.unredirected_hdrs)

    def test_no_auth_redirect_handler_https_to_http_downgrade(self):
        """Should strip headers when redirecting from HTTPS to HTTP on same origin."""
        req = urllib.request.Request(
            "https://api.github.com/test",
            headers={"Authorization": "token secret", "Cookie": "session=123"},
        )
        req.add_unredirected_header("Authorization", "token unredirected")
        handler = check_version_freshness.NoAuthRedirectHandler()
        with patch("urllib.request.HTTPRedirectHandler.redirect_request") as mock_super:
            mock_req = urllib.request.Request(
                "http://api.github.com/test2",
                headers=req.headers,
            )
            mock_req.unredirected_hdrs = req.unredirected_hdrs.copy()
            mock_super.return_value = mock_req
            redirected_req = handler.redirect_request(
                req,
                MagicMock(),
                302,
                "Found",
                MagicMock(),
                "http://api.github.com/test2",
            )
            self.assertNotIn("Authorization", redirected_req.headers)
            self.assertNotIn("Cookie", redirected_req.headers)
            self.assertNotIn("Authorization", redirected_req.unredirected_hdrs)

    def test_no_auth_redirect_handler_same_origin(self):
        """Should retain Authorization header when redirecting to the same origin."""
        req = urllib.request.Request(
            "https://api.github.com/test",
            headers={"Authorization": "token secret", "Cookie": "session=123"},
        )
        handler = check_version_freshness.NoAuthRedirectHandler()
        with patch("urllib.request.HTTPRedirectHandler.redirect_request") as mock_super:
            mock_super.return_value = urllib.request.Request(
                "https://api.github.com/test2",
                headers=req.headers,
            )
            redirected_req = handler.redirect_request(
                req,
                MagicMock(),
                302,
                "Found",
                MagicMock(),
                "https://api.github.com/test2",
            )
            self.assertIn("Authorization", redirected_req.headers)
            self.assertIn("Cookie", redirected_req.headers)

    # ------------------------------------------------------------------
    # Regression: GitHub REST API returns snake_case tag_name, not camelCase
    # ------------------------------------------------------------------

    @patch("check_version_freshness._opener.open")
    def test_check_plugin_uses_snake_case_tag_name(self, mock_urlopen):
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
            result = check_version_freshness.check_plugin(plugin, "n24q02m")

        self.assertEqual(result["status"], "up-to-date")
        self.assertEqual(result["marketplace_ver"], "3.4.5")

    # ------------------------------------------------------------------
    # Error handling for marketplace.json loading
    # ------------------------------------------------------------------

    @patch("check_version_freshness.open", side_effect=OSError("Disk error"))
    @patch("builtins.print")
    def test_check_version_freshness_load_oserror(self, mock_print, mock_open):
        check_version_freshness.check_version_freshness()
        mock_print.assert_called_once()
        args, _ = mock_print.call_args
        self.assertIn("Failed to load marketplace.json: Disk error", args[0])
        self.assertIn("::error ::", args[0])

    @patch("check_version_freshness.open", create=True)
    @patch("json.load", side_effect=json.JSONDecodeError("Expecting value", "", 0))
    @patch("builtins.print")
    def test_check_version_freshness_load_json_error(
        self, mock_print, mock_json_load, mock_open
    ):
        check_version_freshness.check_version_freshness()
        mock_print.assert_called_once()
        args, _ = mock_print.call_args
        self.assertIn("Failed to load marketplace.json: Expecting value", args[0])
        self.assertIn("::error ::", args[0])

    # GraphQL Batch Fetching
    # ------------------------------------------------------------------

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=False)
    @patch("check_version_freshness._opener.open")
    def test_fetch_latest_tags_graphql_success(self, mock_urlopen):
        owner = "test-owner"
        repo_names = ["repo-a", "repo-b"]

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "data": {
                    "repo_repo_a": {"latestRelease": {"tagName": "v1.2.3"}},
                    "repo_repo_b": {"latestRelease": {"tagName": "v2.0.0"}},
                }
            }
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        check_version_freshness._fetch_latest_tags_graphql(owner, repo_names)

        self.assertEqual(
            check_version_freshness._latest_tag_cache.get("test-owner/repo-a"),
            ("ok", "1.2.3"),
        )
        self.assertEqual(
            check_version_freshness._latest_tag_cache.get("test-owner/repo-b"),
            ("ok", "2.0.0"),
        )
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=False)
    @patch("check_version_freshness._opener.open")
    def test_check_version_freshness_uses_graphql(self, mock_urlopen):
        # Mock marketplace.json
        marketplace_data = {
            "owner": {"name": "test-owner"},
            "plugins": [
                {"name": "plugin-a", "source": "./plugins/plugin-a"},
                {"name": "plugin-b", "source": "./plugins/plugin-b"},
            ],
        }

        # Mock GraphQL response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "data": {
                    "repo_plugin_a": {"latestRelease": {"tagName": "v1.0.0"}},
                    "repo_plugin_b": {"latestRelease": {"tagName": "v2.0.0"}},
                }
            }
        ).encode()
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        with (
            patch("builtins.open", create=True),
            patch("json.load", return_value=marketplace_data),
            patch(
                "check_version_freshness._get_marketplace_version", return_value="1.0.0"
            ),
        ):
            # We don't want to actually run the ThreadPoolExecutor logic fully if it's too complex to mock perfectly,
            # but we want to see if GraphQL is called.
            # Actually, check_version_freshness calls _fetch_latest_tags_graphql first.
            check_version_freshness.check_version_freshness()

        # Verify GraphQL was called
        args, _ = mock_urlopen.call_args
        req = args[0]
        self.assertEqual(req.full_url, "https://api.github.com/graphql")

        # Verify cache was populated
        self.assertEqual(
            check_version_freshness._latest_tag_cache.get("test-owner/plugin-a"),
            ("ok", "1.0.0"),
        )
        self.assertEqual(
            check_version_freshness._latest_tag_cache.get("test-owner/plugin-b"),
            ("ok", "2.0.0"),
        )

    # Direct tests for get_latest_tag_api
    # ------------------------------------------------------------------

    @patch("check_version_freshness._opener.open")
    def test_get_latest_tag_api_success(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v1.2.3"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        status, tag = check_version_freshness.get_latest_tag_api("org/repo")
        self.assertEqual(status, "ok")
        self.assertEqual(tag, "1.2.3")

    @patch("check_version_freshness._opener.open")
    def test_get_latest_tag_api_404(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 404, "Not Found", {}, None
        )

        status, tag = check_version_freshness.get_latest_tag_api("org/repo")
        self.assertEqual(status, "no-release")
        self.assertIsNone(tag)

    @patch("check_version_freshness._opener.open")
    def test_get_latest_tag_api_timeout(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError(reason=TimeoutError())

        status, tag = check_version_freshness.get_latest_tag_api("org/repo")
        self.assertEqual(status, "timeout")
        self.assertIsNone(tag)

    @patch("check_version_freshness._opener.open")
    def test_get_latest_tag_api_url_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError(reason="some error")

        status, tag = check_version_freshness.get_latest_tag_api("org/repo")
        self.assertEqual(status, "error")
        self.assertIn("some error", tag)

    @patch("check_version_freshness._opener.open")
    def test_get_latest_tag_api_generic_exception(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("unexpected")

        status, tag = check_version_freshness.get_latest_tag_api("org/repo")
        self.assertEqual(status, "error")
        self.assertEqual(tag, "unexpected")


if __name__ == "__main__":
    unittest.main()

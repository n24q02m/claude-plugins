import re

with open("scripts/test_check_version_freshness.py") as f:
    text = f.read()

# Replace test_check_plugin_valid_name mock
text = re.sub(
    r'@patch\("check_version_freshness.urllib.request.urlopen"\)\n    @patch\("check_version_freshness.os.path.exists"\)\n    def test_check_plugin_valid_name\(self, mock_exists, mock_urlopen\):\n        plugin = \{"name": "valid-plugin-123", "source": "\./plugins/valid-plugin-123"\}\n        mock_exists.return_value = True',
    r'@patch("check_version_freshness.urllib.request.urlopen")\n    def test_check_plugin_valid_name(self, mock_urlopen):\n        plugin = {"name": "valid-plugin-123", "source": "./plugins/valid-plugin-123"}',
    text
)

# Replace test_check_plugin_stale mock
text = re.sub(
    r'@patch\("check_version_freshness.urllib.request.urlopen"\)\n    @patch\("check_version_freshness.os.path.exists", return_value=True\)\n    def test_check_plugin_stale\(self, _mock_exists, mock_urlopen\):',
    r'@patch("check_version_freshness.urllib.request.urlopen")\n    def test_check_plugin_stale(self, mock_urlopen):',
    text
)

# Replace test_check_plugin_no_release_404 mock
text = re.sub(
    r'@patch\("check_version_freshness.urllib.request.urlopen"\)\n    @patch\("check_version_freshness.os.path.exists", return_value=True\)\n    def test_check_plugin_no_release_404\(self, _mock_exists, mock_urlopen\):',
    r'@patch("check_version_freshness.urllib.request.urlopen")\n    def test_check_plugin_no_release_404(self, mock_urlopen):',
    text
)

# Replace test_check_plugin_timeout mock
text = re.sub(
    r'@patch\("check_version_freshness.urllib.request.urlopen"\)\n    @patch\("check_version_freshness.os.path.exists", return_value=True\)\n    def test_check_plugin_timeout\(self, _mock_exists, mock_urlopen\):',
    r'@patch("check_version_freshness.urllib.request.urlopen")\n    def test_check_plugin_timeout(self, mock_urlopen):',
    text
)

# Replace test_check_plugin_error_generic mock
text = re.sub(
    r'@patch\("check_version_freshness.urllib.request.urlopen"\)\n    @patch\("check_version_freshness.os.path.exists", return_value=True\)\n    def test_check_plugin_error_generic\(self, _mock_exists, mock_urlopen\):',
    r'@patch("check_version_freshness.urllib.request.urlopen")\n    def test_check_plugin_error_generic(self, mock_urlopen):',
    text
)

# Replace test_check_plugin_uses_auth_header mock
text = re.sub(
    r'@patch.dict\("os.environ", \{"GITHUB_TOKEN": "secret-token"\}, clear=False\)\n    @patch\("check_version_freshness.urllib.request.urlopen"\)\n    @patch\("check_version_freshness.os.path.exists", return_value=True\)\n    def test_check_plugin_uses_auth_header\(\n        self, _mock_exists, mock_urlopen\n    \):',
    r'@patch.dict("os.environ", {"GITHUB_TOKEN": "secret-token"}, clear=False)\n    @patch("check_version_freshness.urllib.request.urlopen")\n    def test_check_plugin_uses_auth_header(\n        self, mock_urlopen\n    ):',
    text
)

# Replace test_check_plugin_uses_snake_case_tag_name mock
text = re.sub(
    r'@patch\("check_version_freshness.urllib.request.urlopen"\)\n    @patch\("check_version_freshness.os.path.exists", return_value=True\)\n    def test_check_plugin_uses_snake_case_tag_name\(\n        self, _mock_exists, mock_urlopen\n    \):',
    r'@patch("check_version_freshness.urllib.request.urlopen")\n    def test_check_plugin_uses_snake_case_tag_name(\n        self, mock_urlopen\n    ):',
    text
)

# Replace test_check_plugin_cache mock
text = re.sub(
    r'with patch\("check_version_freshness.os.path.exists", return_value=False\):\n            check_version_freshness.check_plugin\(plugin\)\n            check_version_freshness.check_plugin\(plugin\)',
    r'with patch("check_version_freshness.open", side_effect=FileNotFoundError, create=True):\n            check_version_freshness.check_plugin(plugin)\n            check_version_freshness.check_plugin(plugin)',
    text
)

# Replace test_check_plugin_gemini_fallback mock
text = re.sub(
    r'@patch\("check_version_freshness.urllib.request.urlopen"\)\n    @patch\("check_version_freshness.os.path.exists"\)\n    def test_check_plugin_gemini_fallback\(self, mock_exists, mock_urlopen\):\n        plugin = \{"name": "gemini-plugin", "source": "\./plugins/gemini-plugin"\}\n        mock_exists.side_effect = lambda path: "gemini-extension.json" in path\n\n        mock_response = MagicMock\(\)\n        mock_response.read.return_value = b\'\{"tag_name": "v2.0.0"\}\'\n        mock_response.__enter__.return_value = mock_response\n        mock_urlopen.return_value = mock_response\n\n        with \(\n            patch\("check_version_freshness.open", create=True\),\n            patch\("json.load", return_value=\{"version": "2.0.0"\}\),\n        \):\n            result = check_version_freshness.check_plugin\(plugin\)',
    r'''@patch("check_version_freshness.urllib.request.urlopen")
    def test_check_plugin_gemini_fallback(self, mock_urlopen):
        plugin = {"name": "gemini-plugin", "source": "./plugins/gemini-plugin"}

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"tag_name": "v2.0.0"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        def mock_open_impl(filename, *args, **kwargs):
            if "plugin.json" in str(filename):
                raise FileNotFoundError()
            return MagicMock()

        with (
            patch("check_version_freshness.open", side_effect=mock_open_impl, create=True),
            patch("json.load", return_value={"version": "2.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin)''',
    text
)

with open("scripts/test_check_version_freshness.py", "w") as f:
    f.write(text)

import re

with open("scripts/test_check_version_freshness.py") as f:
    text = f.read()

# Instead of removing the patch entirely, I'll keep the decorators but return True / default value,
# and patch `builtins.open` to handle EAFP correctly. Actually, let's keep the `mock_exists` patch
# returning True, but just patch `builtins.open`. The code in `check_version_freshness.py` NO LONGER uses `os.path.exists`.
# Wait, if `check_version_freshness.py` doesn't use `os.path.exists`, then patching it does nothing, which is fine,
# BUT `patch("check_version_freshness.open", ...)` needs to mock `open` in the `check_version_freshness` namespace correctly.

text = re.sub(
    r'@patch\("check_version_freshness.os.path.exists"\)',
    r'',
    text
)

text = re.sub(
    r'@patch\("check_version_freshness.os.path.exists", return_value=True\)',
    r'',
    text
)

text = re.sub(
    r'with patch\("check_version_freshness.os.path.exists", return_value=False\):',
    r'with patch("builtins.open", side_effect=FileNotFoundError):',
    text
)

text = re.sub(
    r'def test_check_plugin_valid_name\(self, mock_exists, mock_urlopen\):',
    r'def test_check_plugin_valid_name(self, mock_urlopen):',
    text
)
text = re.sub(
    r'mock_exists.return_value = True\n\n        mock_response = MagicMock\(\)',
    r'mock_response = MagicMock()',
    text
)

text = re.sub(
    r'def test_check_plugin_stale\(self, _mock_exists, mock_urlopen\):',
    r'def test_check_plugin_stale(self, mock_urlopen):',
    text
)

text = re.sub(
    r'def test_check_plugin_no_release_404\(self, _mock_exists, mock_urlopen\):',
    r'def test_check_plugin_no_release_404(self, mock_urlopen):',
    text
)

text = re.sub(
    r'def test_check_plugin_timeout\(self, _mock_exists, mock_urlopen\):',
    r'def test_check_plugin_timeout(self, mock_urlopen):',
    text
)

text = re.sub(
    r'def test_check_plugin_error_generic\(self, _mock_exists, mock_urlopen\):',
    r'def test_check_plugin_error_generic(self, mock_urlopen):',
    text
)

text = re.sub(
    r'def test_check_plugin_uses_auth_header\(\n        self, _mock_exists, mock_urlopen\n    \):',
    r'def test_check_plugin_uses_auth_header(\n        self, mock_urlopen\n    ):',
    text
)

text = re.sub(
    r'def test_check_plugin_uses_snake_case_tag_name\(\n        self, _mock_exists, mock_urlopen\n    \):',
    r'def test_check_plugin_uses_snake_case_tag_name(\n        self, mock_urlopen\n    ):',
    text
)

text = re.sub(
    r'def test_check_plugin_gemini_fallback\(self, mock_exists, mock_urlopen\):\n        plugin = \{"name": "gemini-plugin", "source": "\./plugins/gemini-plugin"\}\n        mock_exists.side_effect = lambda path: "gemini-extension.json" in path',
    r'''def test_check_plugin_gemini_fallback(self, mock_urlopen):
        plugin = {"name": "gemini-plugin", "source": "./plugins/gemini-plugin"}
''',
    text
)

text = re.sub(
    r'with \(\n            patch\("check_version_freshness.open", create=True\),\n            patch\("json.load", return_value=\{"version": "2.0.0"\}\),\n        \):\n            result = check_version_freshness.check_plugin\(plugin\)',
    r'''def mock_open_impl(filename, *args, **kwargs):
            if "plugin.json" in str(filename):
                raise FileNotFoundError()
            return MagicMock()

        with (
            patch("builtins.open", side_effect=mock_open_impl, create=True),
            patch("json.load", return_value={"version": "2.0.0"}),
        ):
            result = check_version_freshness.check_plugin(plugin)''',
    text
)

text = re.sub(
    r'patch\("check_version_freshness.open", create=True\)',
    r'patch("builtins.open", create=True)',
    text
)


with open("scripts/test_check_version_freshness.py", "w") as f:
    f.write(text)

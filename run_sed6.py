import re

with open("scripts/test_check_version_freshness.py") as f:
    text = f.read()

# Replace test_check_plugin_valid_name patch for open
text = re.sub(
    r'with \(\n            patch\("check_version_freshness.open", create=True\),\n            patch\("json.load", return_value=\{"version": "1.0.0"\}\),\n        \):',
    r'with (\n            patch("builtins.open", create=True),\n            patch("json.load", return_value={"version": "1.0.0"}),\n        ):',
    text
)

# Same for gemini fallback patch
text = re.sub(
    r'with \(\n            patch\("check_version_freshness.open", side_effect=mock_open_impl, create=True\),\n            patch\("json.load", return_value=\{"version": "2.0.0"\}\),\n        \):',
    r'with (\n            patch("builtins.open", side_effect=mock_open_impl, create=True),\n            patch("json.load", return_value={"version": "2.0.0"}),\n        ):',
    text
)

# And for snake case
text = re.sub(
    r'with \(\n            patch\("check_version_freshness.open", create=True\),\n            patch\("json.load", return_value=\{"version": "3.4.5"\}\),\n        \):',
    r'with (\n            patch("builtins.open", create=True),\n            patch("json.load", return_value={"version": "3.4.5"}),\n        ):',
    text
)

# And for cache test
text = re.sub(
    r'with patch\("check_version_freshness.open", side_effect=FileNotFoundError, create=True\):',
    r'with patch("builtins.open", side_effect=FileNotFoundError, create=True):',
    text
)


with open("scripts/test_check_version_freshness.py", "w") as f:
    f.write(text)

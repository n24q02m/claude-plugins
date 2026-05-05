import re

with open("scripts/test_check_version_freshness.py") as f:
    text = f.read()

# Since check_version_freshness.py uses `open`, we need to patch `builtins.open`.
text = text.replace('patch("check_version_freshness.open", create=True)', 'patch("builtins.open")')
text = text.replace('patch("check_version_freshness.open", side_effect=mock_open_impl, create=True)', 'patch("builtins.open", side_effect=mock_open_impl)')
text = text.replace('patch("check_version_freshness.open", side_effect=FileNotFoundError, create=True)', 'patch("builtins.open", side_effect=FileNotFoundError)')


with open("scripts/test_check_version_freshness.py", "w") as f:
    f.write(text)

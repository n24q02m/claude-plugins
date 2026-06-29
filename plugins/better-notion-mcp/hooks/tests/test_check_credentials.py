import unittest
import os
import importlib.util
import sys

# Add plugins directory to sys.path to import the base class and hook module
plugins_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if plugins_path not in sys.path:
    sys.path.append(plugins_path)

# ruff: noqa: E402
from tests.check_credentials_test_base import BaseTestCheckCredentials

# Load the hook module
hook_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "check-credentials.py")
)
spec = importlib.util.spec_from_file_location("check_credentials", hook_path)
check_credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_credentials)


class TestCheckCredentials(BaseTestCheckCredentials, unittest.TestCase):
    check_credentials = check_credentials
    env_key = "NOTION_TOKEN"
    env_value = "secret_123"
    tool_name = "list_pages"
    server_name = "better-notion-mcp"
    is_blocking = False


if __name__ == "__main__":
    unittest.main()

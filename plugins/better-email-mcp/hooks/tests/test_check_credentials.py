import unittest
import os
import sys
import importlib.util

# Add plugins directory to sys.path to import base class
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "tests"))
)
from mcp_hook_test_base import CheckCredentialsTestBase

# Load the hook module
hook_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "check-credentials.py")
)
spec = importlib.util.spec_from_file_location("check_credentials", hook_path)
check_credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_credentials)


class TestCheckCredentials(unittest.TestCase, CheckCredentialsTestBase):
    hook_module = check_credentials
    env_vars = {"EMAIL_CREDENTIALS": "some_creds"}
    server_name = "better-email-mcp"

    def test_main_not_configured_hint(self):
        self.verify_main_not_configured(blocking=False)


if __name__ == "__main__":
    unittest.main()

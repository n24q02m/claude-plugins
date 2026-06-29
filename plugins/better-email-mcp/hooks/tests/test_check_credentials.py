import unittest
import os
import sys

# Add plugins directory to sys.path
plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if plugins_dir not in sys.path:
    sys.path.append(plugins_dir)

from tests.hook_test_base import HookTestBase  # noqa: E402


class TestCheckCredentials(HookTestBase):
    hook_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "check-credentials.py")
    )
    credential_keys = ["EMAIL_CREDENTIALS"]
    server_name = "better-email-mcp"
    is_blocking = False


if __name__ == "__main__":
    unittest.main()

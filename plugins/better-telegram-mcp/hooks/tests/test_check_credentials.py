import unittest
from unittest.mock import patch
import os
import sys
import importlib.util
import io
import json

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
    env_vars = {"TELEGRAM_PHONE": "123456789"}
    server_name = "better-telegram-mcp"

    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token123"}, clear=True)
    def test_is_configured_bot(self):
        self.assertTrue(check_credentials._is_configured())

    def test_main_blocked(self):
        self.verify_main_not_configured(blocking=True)

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": 123})))
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_invalid_tool_name_type(self, mock_stdout, mock_exit, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(SystemExit):
            check_credentials.main()

        mock_exit.assert_called_with(2)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output["decision"], "block")
        self.assertIn(
            "better-telegram-mcp credentials not configured", output["reason"]
        )


if __name__ == "__main__":
    unittest.main()

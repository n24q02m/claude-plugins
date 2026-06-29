import unittest
from unittest.mock import patch
import json
import io
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
    credential_keys = ["TELEGRAM_PHONE", "TELEGRAM_BOT_TOKEN"]
    server_name = "better-telegram-mcp"
    is_blocking = True

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": 123})))
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_invalid_tool_name_type(self, mock_stdout, mock_exit, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(SystemExit):
            self.check_credentials.main()

        mock_exit.assert_called_with(2)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output["decision"], "block")
        self.assertIn(
            "better-telegram-mcp credentials not configured", output["reason"]
        )


if __name__ == "__main__":
    unittest.main()

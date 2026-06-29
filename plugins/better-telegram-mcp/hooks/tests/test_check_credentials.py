import unittest
from unittest.mock import patch
import json
import io
import os
import importlib.util

# Load the hook module
hook_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "check-credentials.py")
)
spec = importlib.util.spec_from_file_location("check_credentials", hook_path)
check_credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_credentials)


class TestCheckCredentials(unittest.TestCase):

    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "send_message"})))
    @patch.dict(os.environ, {"TELEGRAM_PHONE": "123456789"}, clear=True)
    @patch("sys.exit", side_effect=SystemExit)
    def test_main_configured_phone(self, mock_exit):
        with self.assertRaises(SystemExit):
            check_credentials.main()
        mock_exit.assert_called_with(0)

    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "send_message"})))
    @patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "token123"}, clear=True)
    @patch("sys.exit", side_effect=SystemExit)
    def test_main_configured_bot(self, mock_exit):
        with self.assertRaises(SystemExit):
            check_credentials.main()
        mock_exit.assert_called_with(0)

    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "send_message"})))
    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("sys.exit", side_effect=SystemExit)
    def test_main_configured_file(self, mock_exit, mock_expanduser, mock_exists):
        mock_expanduser.return_value = "/home/user"
        mock_exists.side_effect = lambda p: p == "/home/user/.config/mcp/config.enc"
        with self.assertRaises(SystemExit):
            check_credentials.main()
        mock_exit.assert_called_with(0)

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists", return_value=False)
    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "send_message"})))
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_blocked(self, mock_stdout, mock_exit, mock_exists):
        with self.assertRaises(SystemExit):
            check_credentials.main()

        mock_exit.assert_called_with(2)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output["decision"], "block")
        self.assertIn(
            "better-telegram-mcp credentials not configured", output["reason"]
        )

    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool__setup"})))
    @patch("sys.exit", side_effect=SystemExit)
    def test_main_exempt_tool(self, mock_exit):
        with self.assertRaises(SystemExit):
            check_credentials.main()
        mock_exit.assert_called_with(0)

    @patch("sys.stdin", io.StringIO("invalid json"))
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_invalid_json(self, mock_stdout, mock_exit):
        with self.assertRaises(SystemExit):
            check_credentials.main()

        mock_exit.assert_called_with(2)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output["decision"], "block")
        self.assertIn(
            "Invalid input: payload must be a JSON dictionary", output["reason"]
        )


if __name__ == "__main__":
    unittest.main()

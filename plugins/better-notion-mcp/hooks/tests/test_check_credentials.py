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

    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool__setup"})))
    @patch("sys.exit", side_effect=SystemExit)
    def test_main_exempt_tool(self, mock_exit):
        with self.assertRaises(SystemExit):
            check_credentials.main()
        mock_exit.assert_called_with(0)

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "get_page"})))
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_hint(self, mock_stdout, mock_exit, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(SystemExit):
            check_credentials.main()

        mock_exit.assert_called_with(0)
        output = json.loads(mock_stdout.getvalue())
        self.assertIn(
            "better-notion-mcp: credentials not yet configured", output["message"]
        )

    @patch.dict(os.environ, {"NOTION_TOKEN": "token123"}, clear=True)
    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "get_page"})))
    @patch("sys.exit", side_effect=SystemExit)
    def test_main_allowed(self, mock_exit):
        with self.assertRaises(SystemExit):
            check_credentials.main()
        mock_exit.assert_called_with(0)


if __name__ == "__main__":
    unittest.main()

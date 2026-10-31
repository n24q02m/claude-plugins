import unittest
from unittest.mock import patch
import os
import sys

# Add plugins directory to sys.path to import mcp_common
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import mcp_common


class TestMcpCommon(unittest.TestCase):

    @patch("sys.stdin.read", return_value='{"key": "value"}')
    def test_read_mcp_hook_input_valid(self, mock_read):
        data = mcp_common.read_mcp_hook_input()
        self.assertEqual(data, {"key": "value"})
        mock_read.assert_called_once_with(64 * 1024)

    @patch("sys.stdin.read", return_value="invalid json")
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout.write")
    def test_read_mcp_hook_input_invalid_json(self, mock_stdout, mock_exit, mock_read):
        with self.assertRaises(SystemExit):
            mcp_common.read_mcp_hook_input()
        mock_exit.assert_called_once_with(2)

    @patch("sys.stdin.read", return_value='["not a dict"]')
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout.write")
    def test_read_mcp_hook_input_not_dict(self, mock_stdout, mock_exit, mock_read):
        with self.assertRaises(SystemExit):
            mcp_common.read_mcp_hook_input()
        mock_exit.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()

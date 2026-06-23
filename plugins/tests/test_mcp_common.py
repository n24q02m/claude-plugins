import unittest
from unittest.mock import patch
import os
import sys
import json
import io

# Add plugins directory to sys.path to import mcp_common
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import mcp_common


class TestMcpCommon(unittest.TestCase):

    @patch.dict(os.environ, {"LOCALAPPDATA": "/fake/localappdata"}, clear=True)
    @patch("os.path.exists")
    def test_is_relay_configured_localappdata(self, mock_exists):
        # Mock exists to return True for the LOCALAPPDATA path
        mock_exists.side_effect = lambda p: p == os.path.join(
            "/fake/localappdata", "mcp", "config.enc"
        )
        self.assertTrue(mcp_common.is_relay_configured())

    @patch.dict(os.environ, {"APPDATA": "/fake/appdata"}, clear=True)
    @patch("os.path.exists")
    def test_is_relay_configured_appdata(self, mock_exists):
        # Mock exists to return True for the APPDATA path
        mock_exists.side_effect = lambda p: p == os.path.join(
            "/fake/appdata", "mcp", "Config", "config.enc"
        )
        self.assertTrue(mcp_common.is_relay_configured())

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.expanduser")
    @patch("os.path.exists")
    def test_is_relay_configured_home(self, mock_exists, mock_expanduser):
        mock_expanduser.return_value = "/fake/home"
        # Mock exists to return True for the home config path
        mock_exists.side_effect = lambda p: p == os.path.join(
            "/fake/home", ".config", "mcp", "config.enc"
        )
        self.assertTrue(mcp_common.is_relay_configured())

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.expanduser")
    @patch("os.path.exists")
    def test_is_relay_configured_not_found(self, mock_exists, mock_expanduser):
        mock_expanduser.return_value = "/fake/home"
        mock_exists.return_value = False
        self.assertFalse(mcp_common.is_relay_configured())

    @patch("sys.stdin.read", return_value='{"key": "value"}')
    def test_read_mcp_hook_input_valid(self, mock_read):
        data = mcp_common.read_mcp_hook_input()
        self.assertEqual(data, {"key": "value"})
        mock_read.assert_called_once_with(64 * 1024)

    @patch("sys.stdin.read", return_value="invalid json")
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_read_mcp_hook_input_invalid_json(self, mock_stdout, mock_exit, mock_read):
        with self.assertRaises(SystemExit):
            mcp_common.read_mcp_hook_input()
        mock_exit.assert_called_once_with(2)

    @patch("sys.stdin.read", return_value='["not a dict"]')
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_read_mcp_hook_input_not_dict(self, mock_stdout, mock_exit, mock_read):
        with self.assertRaises(SystemExit):
            mcp_common.read_mcp_hook_input()
        mock_exit.assert_called_once_with(2)

    @patch("mcp_common.read_mcp_hook_input")
    @patch("sys.exit")
    def test_check_mcp_credentials_exempt(self, mock_exit, mock_read_input):
        mock_read_input.return_value = {"tool_name": "test_tool__setup"}
        mcp_common.check_mcp_credentials("test-server", ["KEY"])
        mock_exit.assert_called_with(0)

    @patch("mcp_common.read_mcp_hook_input")
    @patch("sys.exit")
    @patch.dict(os.environ, {"KEY": "value"}, clear=True)
    def test_check_mcp_credentials_configured_env(self, mock_exit, mock_read_input):
        mock_read_input.return_value = {"tool_name": "test_tool"}
        mcp_common.check_mcp_credentials("test-server", ["KEY"])
        mock_exit.assert_called_with(0)

    @patch("mcp_common.read_mcp_hook_input")
    @patch("mcp_common.is_relay_configured", return_value=True)
    @patch("sys.exit")
    @patch.dict(os.environ, {}, clear=True)
    def test_check_mcp_credentials_configured_relay(
        self, mock_exit, mock_relay, mock_read_input
    ):
        mock_read_input.return_value = {"tool_name": "test_tool"}
        mcp_common.check_mcp_credentials("test-server", ["KEY"])
        mock_exit.assert_called_with(0)

    @patch("mcp_common.read_mcp_hook_input")
    @patch("mcp_common.is_relay_configured", return_value=False)
    @patch("sys.exit")
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch.dict(os.environ, {}, clear=True)
    def test_check_mcp_credentials_blocking_fail(
        self, mock_stdout, mock_exit, mock_relay, mock_read_input
    ):
        mock_read_input.return_value = {"tool_name": "test_tool"}
        mcp_common.check_mcp_credentials("test-server", ["KEY"], is_blocking=True)
        mock_exit.assert_called_with(2)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output["decision"], "block")
        self.assertIn("test-server credentials not configured", output["reason"])

    @patch("mcp_common.read_mcp_hook_input")
    @patch("mcp_common.is_relay_configured", return_value=False)
    @patch("sys.exit")
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch.dict(os.environ, {}, clear=True)
    def test_check_mcp_credentials_non_blocking_fail(
        self, mock_stdout, mock_exit, mock_relay, mock_read_input
    ):
        mock_read_input.return_value = {"tool_name": "test_tool"}
        mcp_common.check_mcp_credentials("test-server", ["KEY"], is_blocking=False)
        mock_exit.assert_called_with(0)
        output = json.loads(mock_stdout.getvalue())
        self.assertIn("test-server: credentials not yet configured", output["message"])

    @patch("mcp_common.read_mcp_hook_input")
    @patch("mcp_common.is_relay_configured", return_value=False)
    @patch("sys.exit")
    @patch("sys.stdout", new_callable=io.StringIO)
    @patch.dict(os.environ, {}, clear=True)
    def test_check_mcp_credentials_custom_message(
        self, mock_stdout, mock_exit, mock_relay, mock_read_input
    ):
        mock_read_input.return_value = {"tool_name": "test_tool"}
        mcp_common.check_mcp_credentials(
            "test-server", ["KEY"], is_blocking=True, custom_message="Custom fail."
        )
        mock_exit.assert_called_with(2)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output["reason"], "Custom fail.")


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add plugins directory to sys.path to import mcp_common
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import mcp_common


class TestMcpCommon(unittest.TestCase):

    def setUp(self):
        mcp_common.is_relay_configured.cache_clear()

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

    @patch.dict(os.environ, {"LOCALAPPDATA": "/fake/localappdata"}, clear=True)
    @patch("os.path.exists")
    def test_is_relay_configured_is_cached(self, mock_exists):
        # Mock exists to return True for the LOCALAPPDATA path
        mock_exists.return_value = True

        # First call
        self.assertTrue(mcp_common.is_relay_configured())
        # Second call
        self.assertTrue(mcp_common.is_relay_configured())

        # Assert os.path.exists was only called during the first execution
        # (It's called multiple times within the function, but only once per path per call)
        # However, because of lru_cache, the entire function body should only run once.
        self.assertGreater(mock_exists.call_count, 0)
        initial_call_count = mock_exists.call_count

        self.assertTrue(mcp_common.is_relay_configured())
        self.assertEqual(mock_exists.call_count, initial_call_count)

    @patch("sys.stdin.read", return_value='{"key": "value"}')
    def test_read_mcp_hook_input_valid(self, mock_read):
        data = mcp_common.read_mcp_hook_input()
        self.assertEqual(data, {"key": "value"})
        mock_read.assert_called_once_with(1024 * 1024)

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

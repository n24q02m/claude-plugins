import unittest
from unittest.mock import patch
import os
import sys

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


if __name__ == "__main__":
    unittest.main()

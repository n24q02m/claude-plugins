import unittest
import os
import json
import io
import importlib.util
from unittest.mock import patch

# Load the hook module dynamically due to hyphen in filename
module_path = os.path.join(os.getcwd(), "plugins/better-telegram-mcp/hooks/check-credentials.py")
spec = importlib.util.spec_from_file_location("check_credentials", module_path)
check_credentials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_credentials)

class TestCheckCredentials(unittest.TestCase):
    @patch.dict(os.environ, {"TELEGRAM_PHONE": "123456"}, clear=True)
    def test_is_configured_env(self):
        self.assertTrue(check_credentials._is_configured())

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    def test_is_configured_file(self, mock_exists):
        mock_exists.side_effect = lambda p: "config.enc" in p
        self.assertTrue(check_credentials._is_configured())

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    def test_is_not_configured(self, mock_exists):
        mock_exists.return_value = False
        self.assertFalse(check_credentials._is_configured())

    @patch("sys.stdin", io.StringIO('{"tool_name": "better-telegram-mcp__setup"}'))
    def test_main_exempt(self):
        with self.assertRaises(SystemExit) as cm:
            check_credentials.main()
        self.assertEqual(cm.exception.code, 0)

    @patch("sys.stdin", io.StringIO('{"tool_name": "send_message"}'))
    def test_main_blocked(self):
        with patch.object(check_credentials, "_is_configured", return_value=False):
            with patch("sys.stdout", new=io.StringIO()) as fake_out:
                with self.assertRaises(SystemExit) as cm:
                    check_credentials.main()
                self.assertEqual(cm.exception.code, 2)
                self.assertIn('"decision": "block"', fake_out.getvalue())

    @patch("sys.stdin", io.StringIO('{"tool_name": "send_message"}'))
    def test_main_allowed(self):
        with patch.object(check_credentials, "_is_configured", return_value=True):
            with self.assertRaises(SystemExit) as cm:
                check_credentials.main()
            self.assertEqual(cm.exception.code, 0)

    @patch("sys.stdin", io.StringIO('invalid'))
    def test_main_invalid_json(self):
        with self.assertRaises(SystemExit) as cm:
            check_credentials.main()
        self.assertEqual(cm.exception.code, 0)

if __name__ == "__main__":
    unittest.main()

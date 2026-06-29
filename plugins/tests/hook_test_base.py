import unittest
from unittest.mock import patch
import json
import io
import os
import importlib.util


class HookTestBase(unittest.TestCase):
    hook_path = None
    credential_keys = []
    server_name = None
    is_blocking = False

    @classmethod
    def setUpClass(cls):
        if cls is HookTestBase:
            return

        if cls.hook_path:
            spec = importlib.util.spec_from_file_location(
                "check_credentials", cls.hook_path
            )
            cls.check_credentials = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.check_credentials)

    def run(self, result=None):
        if self.__class__ is HookTestBase:
            return
        return super().run(result)

    def test_is_configured_env(self):
        for key in self.credential_keys:
            with patch.dict(os.environ, {key: "secret_123"}, clear=True):
                self.assertTrue(self.check_credentials._is_configured())

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    def test_is_configured_file(self, mock_expanduser, mock_exists):
        mock_expanduser.return_value = "/home/user"
        # Mocking exists to return True only for the home config path
        mock_exists.side_effect = lambda p: p == os.path.join(
            "/home/user", ".config", "mcp", "config.enc"
        )
        self.assertTrue(self.check_credentials._is_configured())

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    def test_not_configured(self, mock_exists):
        mock_exists.return_value = False
        self.assertFalse(self.check_credentials._is_configured())

    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool__setup"})))
    @patch("sys.exit", side_effect=SystemExit)
    def test_main_exempt_tool(self, mock_exit):
        with self.assertRaises(SystemExit):
            self.check_credentials.main()
        mock_exit.assert_called_with(0)

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    @patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool"})))
    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_unconfigured(self, mock_stdout, mock_exit, mock_exists):
        mock_exists.return_value = False
        with self.assertRaises(SystemExit):
            self.check_credentials.main()

        if self.is_blocking:
            mock_exit.assert_called_with(2)
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output["decision"], "block")
            self.assertIn(self.server_name, output["reason"])
        else:
            mock_exit.assert_called_with(0)
            output = json.loads(mock_stdout.getvalue())
            self.assertIn("message", output)
            self.assertIn(self.server_name, output["message"])

    def test_main_configured_allowed(self):
        for key in self.credential_keys:
            with patch.dict(os.environ, {key: "secret_123"}, clear=True), patch(
                "sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool"}))
            ), patch("sys.exit", side_effect=SystemExit) as mock_exit:
                with self.assertRaises(SystemExit):
                    self.check_credentials.main()
                mock_exit.assert_called_with(0)

    @patch("sys.stdin", io.StringIO("invalid json"))
    @patch("sys.exit", side_effect=SystemExit(2))
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_invalid_json(self, mock_stdout, mock_exit):
        with self.assertRaises(SystemExit) as cm:
            self.check_credentials.main()

        self.assertEqual(cm.exception.code, 2)
        mock_exit.assert_called_with(2)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output["decision"], "block")
        self.assertIn(
            "Invalid input: payload must be a JSON dictionary", output["reason"]
        )

    @patch("sys.stdin", io.StringIO('["not a dict"]'))
    @patch("sys.exit", side_effect=SystemExit(2))
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_not_dict_json(self, mock_stdout, mock_exit):
        with self.assertRaises(SystemExit) as cm:
            self.check_credentials.main()

        self.assertEqual(cm.exception.code, 2)
        mock_exit.assert_called_with(2)
        output = json.loads(mock_stdout.getvalue())
        self.assertEqual(output["decision"], "block")
        self.assertIn(
            "Invalid input: payload must be a JSON dictionary", output["reason"]
        )

from unittest.mock import patch
import json
import io
import os


class BaseTestCheckCredentials:
    # To be overridden by subclasses
    check_credentials = None
    env_key = None
    env_value = None
    tool_name = None
    server_name = None
    is_blocking = False

    def test_is_configured_env(self):
        with patch.dict(os.environ, {self.env_key: self.env_value}, clear=True):
            self.assertTrue(self.check_credentials._is_configured())

    def test_is_configured_file(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "os.path.exists"
        ) as mock_exists, patch("os.path.expanduser") as mock_expanduser:
            mock_expanduser.return_value = "/home/user"
            # Mocking exists to return True only for the home config path
            mock_exists.side_effect = lambda p: p == "/home/user/.config/mcp/config.enc"
            self.assertTrue(self.check_credentials._is_configured())

    def test_not_configured(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "os.path.exists"
        ) as mock_exists:
            mock_exists.return_value = False
            self.assertFalse(self.check_credentials._is_configured())

    def test_main_exempt_tool(self):
        with patch(
            "sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool__setup"}))
        ), patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with self.assertRaises(SystemExit):
                self.check_credentials.main()
            mock_exit.assert_called_with(0)

    def test_main_invalid_json(self):
        with patch("sys.stdin", io.StringIO("invalid json")), patch(
            "sys.exit", side_effect=SystemExit
        ) as mock_exit, patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit) as cm:
                self.check_credentials.main()

            self.assertTrue(cm.exception.code == 2 or cm.exception.code is None)
            mock_exit.assert_called_with(2)
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output["decision"], "block")
            self.assertIn("Invalid input", output["reason"])

    def test_main_not_dict_json(self):
        with patch("sys.stdin", io.StringIO('["not a dict"]')), patch(
            "sys.exit", side_effect=SystemExit
        ) as mock_exit, patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            with self.assertRaises(SystemExit) as cm:
                self.check_credentials.main()

            self.assertTrue(cm.exception.code == 2 or cm.exception.code is None)
            mock_exit.assert_called_with(2)
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output["decision"], "block")
            self.assertIn("Invalid input", output["reason"])

    def test_main_not_configured_behavior(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "os.path.exists"
        ) as mock_exists, patch(
            "sys.stdin", io.StringIO(json.dumps({"tool_name": self.tool_name}))
        ), patch(
            "sys.exit", side_effect=SystemExit
        ) as mock_exit, patch(
            "sys.stdout", new_callable=io.StringIO
        ) as mock_stdout:

            mock_exists.return_value = False
            with self.assertRaises(SystemExit):
                self.check_credentials.main()

            if self.is_blocking:
                mock_exit.assert_called_with(2)
                output = json.loads(mock_stdout.getvalue())
                self.assertEqual(output["decision"], "block")
                self.assertIn(
                    f"{self.server_name} credentials not configured", output["reason"]
                )
            else:
                mock_exit.assert_called_with(0)
                output = json.loads(mock_stdout.getvalue())
                self.assertIn("message", output)
                self.assertIn(
                    f"{self.server_name}: credentials not yet configured",
                    output["message"],
                )

    def test_main_configured_allowed(self):
        with patch.dict(os.environ, {self.env_key: self.env_value}, clear=True), patch(
            "sys.stdin", io.StringIO(json.dumps({"tool_name": self.tool_name}))
        ), patch("sys.exit", side_effect=SystemExit) as mock_exit:

            with self.assertRaises(SystemExit):
                self.check_credentials.main()
            mock_exit.assert_called_with(0)

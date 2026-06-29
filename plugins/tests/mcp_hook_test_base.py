from unittest.mock import patch
import json
import io
import os


class CheckCredentialsTestBase:
    """Base class for testing MCP check-credentials hooks."""

    hook_module = None  # To be set by subclasses
    env_vars = {}  # To be set by subclasses (e.g., {"EMAIL_CREDENTIALS": "..."})
    server_name = ""  # To be set by subclasses (e.g., "better-email-mcp")

    def test_is_configured_env(self):
        with patch.dict(os.environ, self.env_vars, clear=True):
            self.assertTrue(self.hook_module._is_configured())

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    @patch("os.path.expanduser")
    def test_is_configured_file(self, mock_expanduser, mock_exists):
        mock_expanduser.return_value = "/home/user"
        mock_exists.side_effect = lambda p: p == "/home/user/.config/mcp/config.enc"
        self.assertTrue(self.hook_module._is_configured())

    @patch.dict(os.environ, {}, clear=True)
    @patch("os.path.exists")
    def test_not_configured(self, mock_exists):
        mock_exists.return_value = False
        self.assertFalse(self.hook_module._is_configured())

    @patch("sys.exit", side_effect=SystemExit)
    def test_main_exempt_tool(self, mock_exit):
        with patch(
            "sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool__setup"}))
        ):
            with self.assertRaises(SystemExit):
                self.hook_module.main()
            mock_exit.assert_called_with(0)

    @patch("sys.exit", side_effect=SystemExit)
    def test_main_allowed(self, mock_exit):
        with patch.dict(os.environ, self.env_vars, clear=True):
            with patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool"}))):
                with self.assertRaises(SystemExit):
                    self.hook_module.main()
                mock_exit.assert_called_with(0)

    @patch("sys.exit", side_effect=SystemExit(2))
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_invalid_json(self, mock_stdout, mock_exit):
        with patch("sys.stdin", io.StringIO("invalid json")):
            with self.assertRaises(SystemExit) as cm:
                self.hook_module.main()
            self.assertEqual(cm.exception.code, 2)
            mock_exit.assert_called_with(2)
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output["decision"], "block")
            self.assertIn("Invalid input", output["reason"])

    @patch("sys.exit", side_effect=SystemExit(2))
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_main_not_dict_json(self, mock_stdout, mock_exit):
        with patch("sys.stdin", io.StringIO('["not a dict"]')):
            with self.assertRaises(SystemExit) as cm:
                self.hook_module.main()
            self.assertEqual(cm.exception.code, 2)
            mock_exit.assert_called_with(2)
            output = json.loads(mock_stdout.getvalue())
            self.assertEqual(output["decision"], "block")
            self.assertIn("Invalid input", output["reason"])

    def verify_main_not_configured(self, blocking=True):
        """Helper to test main when not configured."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.path.exists", return_value=False):
                with patch(
                    "sys.stdin", io.StringIO(json.dumps({"tool_name": "any_tool"}))
                ):
                    with patch("sys.exit", side_effect=SystemExit) as mock_exit:
                        with patch(
                            "sys.stdout", new_callable=io.StringIO
                        ) as mock_stdout:
                            with self.assertRaises(SystemExit):
                                self.hook_module.main()

                            expected_exit_code = 2 if blocking else 0
                            mock_exit.assert_called_with(expected_exit_code)

                            output = json.loads(mock_stdout.getvalue())
                            if blocking:
                                self.assertEqual(output["decision"], "block")
                                self.assertIn(
                                    f"{self.server_name} credentials not configured",
                                    output["reason"],
                                )
                            else:
                                self.assertIn("message", output)
                                self.assertIn(
                                    f"{self.server_name}: credentials not yet configured",
                                    output["message"],
                                )

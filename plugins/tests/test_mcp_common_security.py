import unittest
from unittest.mock import patch
import os
import sys
import json

# Add plugins directory to sys.path to import mcp_common
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import mcp_common


class TestMcpCommonSecurity(unittest.TestCase):

    @patch("sys.exit", side_effect=SystemExit)
    @patch("sys.stdout")
    def test_read_mcp_hook_input_overflow(self, mock_stdout, mock_exit):
        limit = 32 * 1024
        # Create a payload that is larger than limit
        padding = "x" * limit
        large_payload = '{"a": "' + padding + '"}'

        with patch("sys.stdin.read") as mock_read:

            def side_effect(size):
                return large_payload[:size]

            mock_read.side_effect = side_effect

            with self.assertRaises(SystemExit):
                mcp_common.read_mcp_hook_input()

            mock_exit.assert_called_with(2)

            # Capture what was printed
            printed = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
            response = json.loads(printed)
            self.assertEqual(response["decision"], "block")
            self.assertIn("exceeds 32KB limit", response["reason"])

    @patch("sys.stdin.read")
    def test_read_mcp_hook_input_exact_limit(self, mock_read):
        limit = 32 * 1024
        # overhead: {"k":" is 6 and "} is 2 = 8
        padding = "v" * (limit - 8)
        exact_payload = '{"k":"' + padding + '"}'
        self.assertEqual(len(exact_payload), limit)

        mock_read.return_value = exact_payload

        data = mcp_common.read_mcp_hook_input()
        self.assertEqual(data["k"], padding)


if __name__ == "__main__":
    unittest.main()

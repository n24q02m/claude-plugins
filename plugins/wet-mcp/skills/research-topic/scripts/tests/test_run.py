import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import sys
import io
import os

# Add the script directory to sys.path so we can import run
script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Mock wet_mcp before importing run if necessary
mock_run_agent = AsyncMock()
mock_module = MagicMock()
mock_module.run_agent = mock_run_agent


class TestRun(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # We need to ensure wet_mcp is in sys.modules so patch doesn't fail
        self.sys_modules_patcher = patch.dict(
            "sys.modules",
            {
                "wet_mcp": MagicMock(),
                "wet_mcp.sources": MagicMock(),
                "wet_mcp.sources.agent_orchestrator": mock_module,
            },
        )
        self.sys_modules_patcher.start()
        import run

        self.run_mod = run

    def tearDown(self):
        self.sys_modules_patcher.stop()

    async def test_main_success(self):
        # Setup mock result
        mock_result = {
            "markdown": "# Research Result\nThis is a [1] test.",
            "sources": [
                {"index": 1, "title": "Test Source", "url": "https://example.com"}
            ],
            "per_url_metadata": [
                {
                    "url": "https://example.com",
                    "extract_strategy": "basic_http",
                    "tokens": 100,
                    "error": None,
                }
            ],
        }
        mock_run_agent.reset_mock()
        mock_run_agent.return_value = mock_result

        # Capture stdout/stderr
        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ):
            exit_code = await self.run_mod.main(["test query"])

            self.assertEqual(exit_code, 0)
            output = mock_stdout.getvalue()
            self.assertIn("# Research Result", output)
            self.assertIn("- [1] Test Source -- https://example.com", output)
            self.assertIn("Per-URL metadata", output)

            # Verify mock call
            mock_run_agent.assert_called_once_with(
                query="test query",
                max_urls=5,
                synthesis_model=None,
                token_budget=10000,
            )

    async def test_main_error_string(self):
        mock_run_agent.reset_mock()
        mock_run_agent.return_value = "An error occurred"

        with patch("sys.stdout", new=io.StringIO()), patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:
            exit_code = await self.run_mod.main(["test query"])

            self.assertEqual(exit_code, 1)
            err_output = mock_stderr.getvalue()
            self.assertIn("An error occurred", err_output)

    async def test_main_custom_args(self):
        mock_run_agent.reset_mock()
        mock_run_agent.return_value = {"markdown": "ok", "sources": []}

        with patch("sys.stdout", new=io.StringIO()), patch(
            "sys.stderr", new=io.StringIO()
        ):
            await self.run_mod.main(
                [
                    "test query",
                    "--max-urls",
                    "10",
                    "--synthesis-model",
                    "test-model",
                    "--token-budget",
                    "5000",
                ]
            )

            mock_run_agent.assert_called_once_with(
                query="test query",
                max_urls=10,
                synthesis_model="test-model",
                token_budget=5000,
            )


if __name__ == "__main__":
    unittest.main()

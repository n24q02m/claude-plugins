import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import io

# Add the parent directory to sys.path so we can import run.py
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import run


class TestRun(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_run_agent = AsyncMock()
        # Mock the module for lazy import in run.py
        self.patcher = patch.dict(
            "sys.modules",
            {
                "wet_mcp": MagicMock(),
                "wet_mcp.sources": MagicMock(),
                "wet_mcp.sources.agent_orchestrator": MagicMock(
                    run_agent=self.mock_run_agent
                ),
            },
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    async def test_main_success(self):
        # Setup mock return value
        self.mock_run_agent.return_value = {
            "markdown": "Synthetic Answer",
            "sources": [
                {"index": 1, "title": "Source 1", "url": "http://example.com/1"}
            ],
            "per_url_metadata": [{"url": "http://example.com/1", "status": "ok"}],
        }

        # Mock stdout and stderr
        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:

            # Call main with a query
            exit_code = await run.main(["research question"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Synthetic Answer", mock_stdout.getvalue())
            self.assertIn(
                "[1] Source 1 -- http://example.com/1", mock_stdout.getvalue()
            )
            self.assertIn(
                "starting -- query='research question'", mock_stderr.getvalue()
            )
            self.assertIn("done -- sources=1", mock_stderr.getvalue())

            # Verify mock was called with correct arguments
            self.mock_run_agent.assert_called_once_with(
                query="research question",
                max_urls=5,
                synthesis_model=None,
                token_budget=10000,
            )

    async def test_main_error(self):
        # Setup mock return value as string (error path in run.py)
        self.mock_run_agent.return_value = "Something went wrong"

        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:

            exit_code = await run.main(["research question"])

            self.assertEqual(exit_code, 1)
            self.assertIn("Something went wrong", mock_stderr.getvalue())
            self.assertIn("error -- Something went wrong", mock_stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

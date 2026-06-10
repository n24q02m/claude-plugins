import unittest
import unittest.mock
import sys
import io
import os
import json
import asyncio

# Setup path to import run.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestRun(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_run_agent = unittest.mock.AsyncMock()
        # Mocking the entire wet_mcp module structure
        self.patcher = unittest.mock.patch.dict(
            sys.modules,
            {
                "wet_mcp": unittest.mock.MagicMock(),
                "wet_mcp.sources": unittest.mock.MagicMock(),
                "wet_mcp.sources.agent_orchestrator": unittest.mock.MagicMock(
                    run_agent=self.mock_run_agent
                ),
            },
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    async def test_main_success(self):
        import run

        self.mock_run_agent.return_value = {
            "markdown": "Research result",
            "sources": [{"index": 1, "title": "Source 1", "url": "http://example.com"}],
            "per_url_metadata": [{"url": "http://example.com", "status": "ok"}],
        }

        stdout = io.StringIO()
        stderr = io.StringIO()

        with unittest.mock.patch("sys.stdout", stdout), unittest.mock.patch(
            "sys.stderr", stderr
        ):
            exit_code = await run.main(["my query", "--max-urls", "3"])

        self.assertEqual(exit_code, 0)
        self.mock_run_agent.assert_called_once_with(
            query="my query", max_urls=3, synthesis_model=None, token_budget=10000
        )

        output = stdout.getvalue()
        self.assertIn("Research result", output)
        self.assertIn("Source 1", output)
        self.assertIn("http://example.com", output)
        self.assertIn("## Sources", output)
        self.assertIn("## Per-URL metadata", output)

    async def test_main_error(self):
        import run

        self.mock_run_agent.return_value = "An error occurred"

        stdout = io.StringIO()
        stderr = io.StringIO()

        with unittest.mock.patch("sys.stdout", stdout), unittest.mock.patch(
            "sys.stderr", stderr
        ):
            exit_code = await run.main(["my query"])

        self.assertEqual(exit_code, 1)
        self.assertIn("error -- An error occurred", stderr.getvalue())
        self.assertIn("An error occurred", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

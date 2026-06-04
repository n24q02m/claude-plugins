import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import io
import sys
import os

# Create a mock for wet_mcp.sources.agent_orchestrator
mock_orchestrator = MagicMock()
sys.modules["wet_mcp"] = MagicMock()
sys.modules["wet_mcp.sources"] = MagicMock()
sys.modules["wet_mcp.sources.agent_orchestrator"] = mock_orchestrator

# Add the directory containing run.py to sys.path
sys.path.append(os.path.dirname(__file__))
from run import main


class TestRun(unittest.IsolatedAsyncioTestCase):
    @patch("run.argparse.ArgumentParser.parse_args")
    async def test_main_success(self, mock_parse_args):
        mock_parse_args.return_value = MagicMock(
            query="test query", max_urls=5, synthesis_model=None, token_budget=10000
        )

        # Setup mock_run_agent
        mock_run_agent = AsyncMock()
        mock_orchestrator.run_agent = mock_run_agent
        mock_run_agent.return_value = {
            "markdown": "Test answer",
            "sources": [{"index": 1, "title": "Source 1", "url": "http://example.com"}],
            "per_url_metadata": [],
        }

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            exit_code = await main([])

        self.assertEqual(exit_code, 0)
        self.assertIn("Test answer", stdout.getvalue())
        self.assertIn("Source 1", stdout.getvalue())
        self.assertIn("[research-topic] starting", stderr.getvalue())
        self.assertIn("[research-topic] done", stderr.getvalue())

        mock_run_agent.assert_called_once_with(
            query="test query", max_urls=5, synthesis_model=None, token_budget=10000
        )

    @patch("run.argparse.ArgumentParser.parse_args")
    async def test_main_error(self, mock_parse_args):
        mock_parse_args.return_value = MagicMock(
            query="test query", max_urls=5, synthesis_model=None, token_budget=10000
        )

        # Setup mock_run_agent
        mock_run_agent = AsyncMock()
        mock_orchestrator.run_agent = mock_run_agent
        mock_run_agent.return_value = "Error message"

        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            exit_code = await main([])

        self.assertEqual(exit_code, 1)
        self.assertIn("Error message", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

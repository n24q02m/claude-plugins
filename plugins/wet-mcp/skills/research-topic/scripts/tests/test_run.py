import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import importlib.util
import io
import json

# Mock wet_mcp before importing run.py
mock_agent_orchestrator = MagicMock()
sys.modules["wet_mcp"] = MagicMock()
sys.modules["wet_mcp.sources"] = MagicMock()
sys.modules["wet_mcp.sources.agent_orchestrator"] = mock_agent_orchestrator

# Load run.py module
script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run.py"))
spec = importlib.util.spec_from_file_location("run_script", script_path)
run_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_script)


class TestRun(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_run_agent = AsyncMock()
        mock_agent_orchestrator.run_agent = self.mock_run_agent

    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("sys.stderr", new_callable=io.StringIO)
    async def test_main_success(self, mock_stderr, mock_stdout):
        self.mock_run_agent.return_value = {
            "markdown": "Test answer",
            "sources": [{"index": 1, "title": "Source 1", "url": "http://example.com"}],
            "per_url_metadata": [{"url": "http://example.com", "status": 200}],
        }

        exit_code = await run_script.main(["how to test?", "--max-urls", "3"])

        self.assertEqual(exit_code, 0)
        self.mock_run_agent.assert_called_once_with(
            query="how to test?", max_urls=3, synthesis_model=None, token_budget=10000
        )

        output = mock_stdout.getvalue()
        self.assertIn("Test answer", output)
        self.assertIn("- [1] Source 1 -- http://example.com", output)
        self.assertIn("## Per-URL metadata", output)

        err_output = mock_stderr.getvalue()
        self.assertIn(
            "[research-topic] starting -- query='how to test?' max_urls=3", err_output
        )
        self.assertIn("[research-topic] done -- sources=1", err_output)

    @patch("sys.stdout", new_callable=io.StringIO)
    @patch("sys.stderr", new_callable=io.StringIO)
    async def test_main_error(self, mock_stderr, mock_stdout):
        self.mock_run_agent.return_value = "Something went wrong"

        exit_code = await run_script.main(["bad query"])

        self.assertEqual(exit_code, 1)
        err_output = mock_stderr.getvalue()
        self.assertIn("[research-topic] error -- Something went wrong", err_output)
        self.assertIn("Something went wrong", err_output)


if __name__ == "__main__":
    unittest.main()

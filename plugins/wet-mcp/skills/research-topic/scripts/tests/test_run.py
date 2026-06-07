import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import io

# Add the script directory to sys.path so we can import run.py
script_dir = os.path.dirname(__file__)
if script_dir not in sys.path:
    sys.path.append(script_dir)

import run


class TestRun(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_run_agent = AsyncMock()
        # Mock the module and the function
        self.mock_orchestrator = MagicMock()
        self.mock_orchestrator.run_agent = self.mock_run_agent

        # Inject into sys.modules to satisfy the lazy import in run.py
        # from wet_mcp.sources.agent_orchestrator import run_agent
        self.patcher = patch.dict(
            sys.modules,
            {
                "wet_mcp": MagicMock(),
                "wet_mcp.sources": MagicMock(),
                "wet_mcp.sources.agent_orchestrator": self.mock_orchestrator,
            },
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    async def test_main_success(self):
        # Success result matches the expected dictionary structure
        self.mock_run_agent.return_value = {
            "markdown": "Success result",
            "sources": [{"index": 1, "title": "Source 1", "url": "http://example.com"}],
            "per_url_metadata": [{"url": "http://example.com", "meta": "data"}],
        }

        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:
            exit_code = await run.main(["test query"])

        self.assertEqual(exit_code, 0)
        stdout_output = mock_stdout.getvalue()
        stderr_output = mock_stderr.getvalue()

        self.assertIn("Success result", stdout_output)
        self.assertIn("[1] Source 1 -- http://example.com", stdout_output)
        self.assertIn("## Per-URL metadata", stdout_output)
        # Check that progress markers were emitted to stderr
        self.assertIn("[research-topic] starting", stderr_output)
        self.assertIn(
            "[research-topic] searching + extracting + synthesising", stderr_output
        )
        self.assertIn("[research-topic] done", stderr_output)

    async def test_main_error_path(self):
        # Error path: run_agent returns a string
        error_msg = "Simulated error from agent"
        self.mock_run_agent.return_value = error_msg

        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:
            exit_code = await run.main(["test query"])

        self.assertEqual(exit_code, 1)
        stderr_output = mock_stderr.getvalue()

        # Verify the progress marker for error was emitted
        self.assertIn(f"[research-topic] error -- {error_msg}", stderr_output)
        # Verify the error string itself was printed to stderr
        self.assertIn(error_msg, stderr_output)
        # Verify the success progress markers are NOT present
        self.assertNotIn("[research-topic] done", stderr_output)


if __name__ == "__main__":
    unittest.main()

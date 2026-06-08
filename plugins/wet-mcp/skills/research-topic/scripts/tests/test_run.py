import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import io
import importlib.util

# Load the run.py module
script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run.py"))
spec = importlib.util.spec_from_file_location("run_script", script_path)
run_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_script)


class TestRunScript(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_run_agent = AsyncMock()
        # Mock the entire wet_mcp.sources.agent_orchestrator module
        # so the lazy import 'from wet_mcp.sources.agent_orchestrator import run_agent' works
        self.mock_orchestrator = MagicMock()
        self.mock_orchestrator.run_agent = self.mock_run_agent

        # We need to ensure that when 'from wet_mcp.sources.agent_orchestrator import run_agent'
        # is executed inside main(), it finds our mock.
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
        self.mock_run_agent.return_value = {
            "markdown": "Success answer",
            "sources": [{"index": 1, "title": "Source 1", "url": "http://example.com"}],
            "per_url_metadata": [],
        }

        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:
            # We pass argv to avoid parsing sys.argv of the test runner
            exit_code = await run_script.main(["my query"])

            self.assertEqual(exit_code, 0)
            stdout_val = mock_stdout.getvalue()
            stderr_val = mock_stderr.getvalue()

            self.assertIn("Success answer", stdout_val)
            self.assertIn("## Sources", stdout_val)
            self.assertIn("- [1] Source 1 -- http://example.com", stdout_val)
            self.assertIn("[research-topic] starting", stderr_val)
            self.assertIn("[research-topic] done -- sources=1", stderr_val)

    async def test_main_error(self):
        error_msg = "Something went wrong"
        self.mock_run_agent.return_value = error_msg

        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:
            exit_code = await run_script.main(["my query"])

            self.assertEqual(exit_code, 1)
            stderr_val = mock_stderr.getvalue()

            self.assertIn(f"[research-topic] error -- {error_msg}", stderr_val)
            self.assertIn(error_msg, stderr_val)
            # Output should not contain success markers
            self.assertNotIn("## Sources", mock_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()

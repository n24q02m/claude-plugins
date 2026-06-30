import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import io
import importlib.util

# Mock the wet_mcp module before loading the script
mock_agent_orchestrator = MagicMock()
mock_run_agent = AsyncMock()
mock_agent_orchestrator.run_agent = mock_run_agent
sys.modules["wet_mcp"] = MagicMock()
sys.modules["wet_mcp.sources"] = MagicMock()
sys.modules["wet_mcp.sources.agent_orchestrator"] = mock_agent_orchestrator

# Dynamically load the run.py script
script_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "scripts", "run.py")
)
spec = importlib.util.spec_from_file_location("run_script", script_path)
run_script = importlib.util.module_from_spec(spec)
sys.modules["run_script"] = run_script
spec.loader.exec_module(run_script)


class TestRunScript(unittest.IsolatedAsyncioTestCase):

    async def test_main_success(self):
        # Mock result from run_agent
        mock_result = {
            "markdown": "Test Answer",
            "sources": [
                {"index": 1, "title": "Source 1", "url": "http://example.com/1"}
            ],
            "per_url_metadata": [{"url": "http://example.com/1", "status": "ok"}],
        }
        mock_run_agent.reset_mock()
        mock_run_agent.return_value = mock_result

        # Capture stdout and stderr
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            exit_code = await run_script.main(["test query", "--max-urls", "2"])

        self.assertEqual(exit_code, 0)
        self.assertIn("Test Answer", stdout.getvalue())
        self.assertIn("## Sources", stdout.getvalue())
        self.assertIn("- [1] Source 1 -- http://example.com/1", stdout.getvalue())
        self.assertIn("## Per-URL metadata", stdout.getvalue())

        # Verify progress markers in stderr
        stderr_val = stderr.getvalue()
        self.assertIn(
            "[research-topic] starting -- query='test query' max_urls=2", stderr_val
        )
        self.assertIn(
            "[research-topic] searching + extracting + synthesising", stderr_val
        )
        self.assertIn("[research-topic] done -- sources=1", stderr_val)

        # Verify run_agent call
        mock_run_agent.assert_called_once_with(
            query="test query", max_urls=2, synthesis_model=None, token_budget=10000
        )

    async def test_main_error(self):
        # Mock error string from run_agent
        mock_run_agent.reset_mock()
        mock_run_agent.return_value = "An error occurred"

        # Capture stdout and stderr
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            exit_code = await run_script.main(["test query"])

        self.assertEqual(exit_code, 1)
        self.assertIn("An error occurred", stderr.getvalue())
        self.assertIn("[research-topic] error -- An error occurred", stderr.getvalue())

    def test_emit_progress(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            run_script._emit_progress("stage", "detail")

        self.assertEqual(stderr.getvalue(), "[research-topic] stage -- detail\n")

    def test_emit_progress_no_detail(self):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            run_script._emit_progress("stage")

        self.assertEqual(stderr.getvalue(), "[research-topic] stage\n")


if __name__ == "__main__":
    unittest.main()

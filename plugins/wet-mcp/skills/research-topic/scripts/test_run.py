import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import io
import os
import sys
import importlib.util

# Load the run module
script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "run.py"))
spec = importlib.util.spec_from_file_location("run", script_path)
run = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run)


class TestRun(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_run_agent = AsyncMock()
        # Mock the module that main() tries to import from
        self.mock_orchestrator = MagicMock()
        self.mock_orchestrator.run_agent = self.mock_run_agent

        # We need to ensure 'wet_mcp.sources' also exists in sys.modules for the import to work
        self.modules_patcher = patch.dict(
            "sys.modules",
            {
                "wet_mcp": MagicMock(),
                "wet_mcp.sources": MagicMock(),
                "wet_mcp.sources.agent_orchestrator": self.mock_orchestrator,
            },
        )
        self.modules_patcher.start()

    def tearDown(self):
        self.modules_patcher.stop()

    async def test_emit_progress(self):
        with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
            run._emit_progress("stage", "detail")
            self.assertEqual(
                mock_stderr.getvalue(), "[research-topic] stage -- detail\n"
            )

    async def test_emit_progress_no_detail(self):
        with patch("sys.stderr", new=io.StringIO()) as mock_stderr:
            run._emit_progress("stage")
            self.assertEqual(mock_stderr.getvalue(), "[research-topic] stage\n")

    async def test_main_success(self):
        self.mock_run_agent.return_value = {
            "markdown": "Answer Text",
            "sources": [{"index": 1, "title": "Source 1", "url": "http://example.com"}],
            "per_url_metadata": [{"url": "http://example.com", "status": "ok"}],
        }

        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:
            exit_code = await run.main(["query"])

            self.assertEqual(exit_code, 0)
            self.assertIn("Answer Text", mock_stdout.getvalue())
            self.assertIn("Source 1", mock_stdout.getvalue())
            self.assertIn("http://example.com", mock_stdout.getvalue())
            self.assertIn("[research-topic] starting", mock_stderr.getvalue())
            self.assertIn("[research-topic] done", mock_stderr.getvalue())

            self.mock_run_agent.assert_called_once_with(
                query="query", max_urls=5, synthesis_model=None, token_budget=10000
            )

    async def test_main_error(self):
        self.mock_run_agent.return_value = "Some error message"

        with patch("sys.stdout", new=io.StringIO()) as mock_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as mock_stderr:
            exit_code = await run.main(["query"])

            self.assertEqual(exit_code, 1)
            self.assertIn(
                "[research-topic] error -- Some error message", mock_stderr.getvalue()
            )
            self.assertIn("Some error message", mock_stderr.getvalue())

    async def test_main_custom_args(self):
        self.mock_run_agent.return_value = {
            "markdown": "Ans",
            "sources": [],
            "per_url_metadata": [],
        }

        with patch("sys.stdout", new=io.StringIO()), patch(
            "sys.stderr", new=io.StringIO()
        ):
            await run.main(
                [
                    "my query",
                    "--max-urls",
                    "10",
                    "--synthesis-model",
                    "gpt-4",
                    "--token-budget",
                    "5000",
                ]
            )

        self.mock_run_agent.assert_called_once_with(
            query="my query", max_urls=10, synthesis_model="gpt-4", token_budget=5000
        )


if __name__ == "__main__":
    unittest.main()

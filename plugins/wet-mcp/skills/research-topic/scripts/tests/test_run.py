import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
import io
import os
import sys
import importlib.util

# Load the run module
script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run.py"))
spec = importlib.util.spec_from_file_location("run_script", script_path)
run_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_script)


class TestRunScript(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Mock the run_agent function
        self.mock_run_agent = AsyncMock()

        # Mock the module that contains run_agent
        self.mock_agent_module = MagicMock()
        self.mock_agent_module.run_agent = self.mock_run_agent

        # Patch sys.modules to provide the mock module for the lazy import
        # Note: We need to mock the full path used in the 'from ... import'
        self.patcher = patch.dict(
            sys.modules,
            {
                "wet_mcp": MagicMock(),
                "wet_mcp.sources": MagicMock(),
                "wet_mcp.sources.agent_orchestrator": self.mock_agent_module,
            },
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    async def test_main_error_path(self):
        # Arrange
        error_message = "Some error occurred"
        self.mock_run_agent.return_value = error_message

        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            # Act
            exit_code = await run_script.main(["test query"])

            # Assert
            self.assertEqual(exit_code, 1)
            stderr_output = mock_stderr.getvalue()
            # _emit_progress outputs Stage -- Detail
            self.assertIn("[research-topic] error -- " + error_message, stderr_output)
            # Then the result string itself is printed to stderr
            self.assertIn(error_message, stderr_output)

            # Verify run_agent was called with correct arguments
            self.mock_run_agent.assert_called_once_with(
                query="test query", max_urls=5, synthesis_model=None, token_budget=10000
            )

    async def test_main_success_path(self):
        # Arrange
        mock_result = {
            "markdown": "Synthesized content",
            "sources": [
                {"index": 1, "title": "Source 1", "url": "http://example.com/1"}
            ],
            "per_url_metadata": [
                {
                    "url": "http://example.com/1",
                    "extract_strategy": "basic_http",
                    "tokens": 100,
                    "error": None,
                }
            ],
        }
        self.mock_run_agent.return_value = mock_result

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch(
            "sys.stderr", new_callable=io.StringIO
        ) as mock_stderr:
            # Act
            exit_code = await run_script.main(["test query", "--max-urls", "10"])

            # Assert
            self.assertEqual(exit_code, 0)
            stdout_output = mock_stdout.getvalue()
            self.assertIn("Synthesized content", stdout_output)
            self.assertIn("## Sources", stdout_output)
            self.assertIn("- [1] Source 1 -- http://example.com/1", stdout_output)
            self.assertIn("## Per-URL metadata", stdout_output)

            # Check JSON output for per_url_metadata
            metadata_json = stdout_output.split("## Per-URL metadata")[-1].strip()
            metadata = json.loads(metadata_json)
            self.assertEqual(metadata, mock_result["per_url_metadata"])

            stderr_output = mock_stderr.getvalue()
            self.assertIn("[research-topic] starting", stderr_output)
            self.assertIn("query='test query' max_urls=10", stderr_output)
            self.assertIn("[research-topic] done -- sources=1", stderr_output)

            # Verify run_agent was called with correct arguments
            self.mock_run_agent.assert_called_once_with(
                query="test query",
                max_urls=10,
                synthesis_model=None,
                token_budget=10000,
            )

    async def test_main_arguments(self):
        # Test custom arguments
        self.mock_run_agent.return_value = {
            "markdown": "",
            "sources": [],
            "per_url_metadata": [],
        }

        with patch("sys.stdout", new_callable=io.StringIO), patch(
            "sys.stderr", new_callable=io.StringIO
        ):
            await run_script.main(
                [
                    "another query",
                    "--max-urls",
                    "3",
                    "--synthesis-model",
                    "gpt-4",
                    "--token-budget",
                    "5000",
                ]
            )

            self.mock_run_agent.assert_called_once_with(
                query="another query",
                max_urls=3,
                synthesis_model="gpt-4",
                token_budget=5000,
            )


if __name__ == "__main__":
    unittest.main()

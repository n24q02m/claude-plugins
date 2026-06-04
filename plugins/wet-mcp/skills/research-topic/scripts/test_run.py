import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import io
import sys
import os
import importlib.util
import json

# Mock the wet_mcp module
sys.modules["wet_mcp"] = MagicMock()
sys.modules["wet_mcp.sources"] = MagicMock()
sys.modules["wet_mcp.sources.agent_orchestrator"] = MagicMock()

# Load the run module
script_dir = os.path.dirname(os.path.abspath(__file__))
script_path = os.path.join(script_dir, "run.py")
spec = importlib.util.spec_from_file_location("run_script", script_path)
run_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_script)


class TestRun(unittest.IsolatedAsyncioTestCase):

    async def test_main_error_path(self):
        # Mock run_agent to return a string (error path)
        mock_run_agent = AsyncMock(return_value="Something went wrong")

        with patch("wet_mcp.sources.agent_orchestrator.run_agent", mock_run_agent):
            stderr = io.StringIO()
            with patch("sys.stderr", stderr):
                # Arguments: query
                result = await run_script.main(["test query"])

            self.assertEqual(result, 1)
            self.assertIn("Something went wrong", stderr.getvalue())
            # Check if progress was emitted to stderr
            self.assertIn(
                "[research-topic] error -- Something went wrong", stderr.getvalue()
            )

    async def test_main_success_path(self):
        # Mock run_agent to return a dict (success path)
        mock_run_agent = AsyncMock(
            return_value={
                "markdown": "# Success Content",
                "sources": [
                    {"index": 1, "title": "Source 1", "url": "http://example.com"}
                ],
                "per_url_metadata": [
                    {"url": "http://example.com", "tokens": 100, "error": None}
                ],
            }
        )

        with patch("wet_mcp.sources.agent_orchestrator.run_agent", mock_run_agent):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
                result = await run_script.main(["test query"])

            self.assertEqual(result, 0)
            output = stdout.getvalue()
            self.assertIn("# Success Content", output)
            self.assertIn("- [1] Source 1 -- http://example.com", output)
            self.assertIn("## Sources", output)
            self.assertIn("## Per-URL metadata", output)

            # Verify metadata is in the output as JSON
            metadata_str = output.split("## Per-URL metadata")[1].strip()
            metadata = json.loads(metadata_str)
            self.assertEqual(len(metadata), 1)
            self.assertEqual(metadata[0]["url"], "http://example.com")

            # Verify progress was emitted to stderr
            self.assertIn("[research-topic] starting", stderr.getvalue())
            self.assertIn("[research-topic] done -- sources=1", stderr.getvalue())

    async def test_main_argument_parsing(self):
        # Test that arguments are parsed correctly and passed to run_agent
        mock_run_agent = AsyncMock(
            return_value={"markdown": "", "sources": [], "per_url_metadata": []}
        )

        with patch("wet_mcp.sources.agent_orchestrator.run_agent", mock_run_agent):
            # Suppress output
            with patch("sys.stdout", io.StringIO()), patch("sys.stderr", io.StringIO()):
                await run_script.main(
                    [
                        "custom query",
                        "--max-urls",
                        "10",
                        "--synthesis-model",
                        "test-model",
                        "--token-budget",
                        "5000",
                    ]
                )

            mock_run_agent.assert_called_once_with(
                query="custom query",
                max_urls=10,
                synthesis_model="test-model",
                token_budget=5000,
            )


if __name__ == "__main__":
    unittest.main()

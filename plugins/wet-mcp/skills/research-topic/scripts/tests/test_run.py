import unittest
from unittest.mock import patch
import io
import os
import importlib.util

# Load the run module
script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "run.py"))
spec = importlib.util.spec_from_file_location("run", script_path)
run_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_module)


class TestRun(unittest.TestCase):
    def test_emit_progress_no_detail(self):
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            run_module._emit_progress("starting")
            self.assertEqual(mock_stderr.getvalue(), "[research-topic] starting\n")

    def test_emit_progress_with_detail(self):
        with patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            run_module._emit_progress("starting", "query='test'")
            self.assertEqual(
                mock_stderr.getvalue(), "[research-topic] starting -- query='test'\n"
            )


if __name__ == "__main__":
    unittest.main()

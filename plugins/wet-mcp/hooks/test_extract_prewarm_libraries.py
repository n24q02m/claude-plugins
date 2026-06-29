import unittest
import sys
from io import StringIO
from extract_prewarm_libraries import extract_libraries, main


class TestExtractPrewarmLibraries(unittest.TestCase):
    def test_basic_python_imports(self):
        text = "import react\nfrom fastapi import FastAPI"
        self.assertEqual(extract_libraries(text), ["fastapi", "react"])

    def test_js_require(self):
        text = 'const next = require("next/router")'
        self.assertEqual(extract_libraries(text), ["next"])

    def test_js_from_string(self):
        text = 'import { useState } from "react"'
        self.assertEqual(extract_libraries(text), ["react"])

        text = 'export * from "vue"'
        self.assertEqual(extract_libraries(text), ["vue"])

    def test_normalization(self):
        text = "import REACT"
        self.assertEqual(extract_libraries(text), ["react"])

    def test_scoped_packages(self):
        # bash sed: s|^@[^/]+/||
        text = 'require("@org/next")'
        self.assertEqual(extract_libraries(text), ["next"])

    def test_no_matches(self):
        text = "nothing interesting here"
        self.assertEqual(extract_libraries(text), [])

    def test_top_20_limit(self):
        # Create 25 unique candidates to test sorting and slicing
        # TIER1_LIBRARIES has 20 items.
        text = "\n".join([f"import lib_{i}" for i in range(25)])
        # extract_libraries first gets all candidates, then sorts and takes top 20.
        # lib_0 to lib_19 (sorted) will be the top 20 candidates.
        # None of them are in TIER1_LIBRARIES.
        self.assertEqual(extract_libraries(text), [])

    def test_mixed_patterns(self):
        text = """
        import pandas as pd
        from sklearn import datasets
        const next = require("next")
        import { something } from "react"
        """
        self.assertEqual(extract_libraries(text), ["next", "pandas", "react"])

    def test_main_with_hits(self):
        input_text = "import react\n"
        stdin = sys.stdin
        stdout = sys.stdout
        sys.stdin = StringIO(input_text)
        sys.stdout = StringIO()
        try:
            main()
            output = sys.stdout.getvalue().strip()
            self.assertEqual(output, "react")
        finally:
            sys.stdin = stdin
            sys.stdout = stdout

    def test_main_no_hits(self):
        input_text = "nothing"
        stdin = sys.stdin
        stdout = sys.stdout
        sys.stdin = StringIO(input_text)
        sys.stdout = StringIO()
        try:
            main()
            output = sys.stdout.getvalue().strip()
            self.assertEqual(output, "")
        finally:
            sys.stdin = stdin
            sys.stdout = stdout

    def test_main_empty_input(self):
        input_text = ""
        stdin = sys.stdin
        stdout = sys.stdout
        sys.stdin = StringIO(input_text)
        sys.stdout = StringIO()
        try:
            main()
            output = sys.stdout.getvalue().strip()
            self.assertEqual(output, "")
        finally:
            sys.stdin = stdin
            sys.stdout = stdout

    def test_main_eof(self):
        # Trigger EOFError during sys.stdin.read()
        stdin = sys.stdin

        class EOFErrorRaisingIO:
            def read(self, *args, **kwargs):
                raise EOFError()

        sys.stdin = EOFErrorRaisingIO()
        try:
            main()
        finally:
            sys.stdin = stdin


if __name__ == "__main__":
    unittest.main()

import unittest
import tempfile
from pathlib import Path
import os
import sys

# Add plugins dir to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    "chat",
    os.path.join(os.path.dirname(__file__), "..", "agent-chat-plugin", "chat.py"),
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
parse_frontmatter = _MOD.parse_frontmatter


class TestChat(unittest.TestCase):
    def test_parse_frontmatter(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            f.write("---\nfrom: a\nto: b, c\n---\nbody\n")
            fname = f.name

        meta = parse_frontmatter(Path(fname))
        self.assertEqual(meta["from"], "a")
        self.assertEqual(meta["to"], "b, c")
        self.assertEqual(meta["to_list"], ["b", "c"])

        os.unlink(fname)


if __name__ == "__main__":
    unittest.main()

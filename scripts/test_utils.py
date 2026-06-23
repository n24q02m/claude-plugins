import unittest
import os
import tempfile
from utils import sanitize_log, PLUGIN_NAME_PATTERN, get_safe_path


class TestUtils(unittest.TestCase):
    def test_sanitize_log_no_special_chars(self):
        """Should return the same string if no special characters are present."""
        self.assertEqual(sanitize_log("hello world"), "hello world")

    def test_sanitize_log_percent(self):
        """Should replace % with %25."""
        self.assertEqual(sanitize_log("percent % sign"), "percent %25 sign")

    def test_sanitize_log_carriage_return(self):
        """Should replace \r with %0D."""
        self.assertEqual(sanitize_log("carriage\rreturn"), "carriage%0Dreturn")

    def test_sanitize_log_newline(self):
        """Should replace \n with %0A."""
        self.assertEqual(sanitize_log("new\nline"), "new%0Aline")

    def test_sanitize_log_all_special_chars(self):
        """Should replace all special characters correctly."""
        self.assertEqual(sanitize_log("%\r\n"), "%25%0D%0A")

    def test_sanitize_log_non_string(self):
        """Should handle non-string input by converting it to string first."""
        self.assertEqual(sanitize_log(123), "123")

    def test_plugin_name_pattern_valid(self):
        """Should match valid plugin names."""
        valid_names = ["plugin-name", "plugin123", "123-plugin", "a", "A", "A-b-C-1"]
        for name in valid_names:
            with self.subTest(name=name):
                self.assertTrue(PLUGIN_NAME_PATTERN.fullmatch(name))

    def test_plugin_name_pattern_invalid(self):
        """Should not match invalid plugin names."""
        invalid_names = [
            "plugin_name",
            "plugin.name",
            "plugin name",
            "plugin!",
            "",
            " ",
        ]
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(PLUGIN_NAME_PATTERN.fullmatch(name))

    def test_get_safe_path_valid(self):
        """Should return relative path for valid sub-paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sub_dir = os.path.join(tmpdir, "sub")
            os.makedirs(sub_dir)

            # Simple sub-path
            self.assertEqual(get_safe_path(tmpdir, "sub"), "sub")
            # Sub-path with .
            self.assertEqual(get_safe_path(tmpdir, "./sub"), "sub")
            # Sub-path with .. that stays inside
            self.assertEqual(get_safe_path(tmpdir, "sub/../sub"), "sub")
            # Base directory itself
            self.assertEqual(get_safe_path(tmpdir, "."), ".")

    def test_get_safe_path_traversal(self):
        """Should raise ValueError for path traversal outside base_dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Traversal using ..
            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                get_safe_path(tmpdir, "..")

            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                get_safe_path(tmpdir, "../etc/passwd")

            # Absolute path traversal (if it goes outside)
            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                get_safe_path(tmpdir, "/etc/passwd")

    def test_get_safe_path_null_bytes(self):
        """Should raise ValueError for paths containing null bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, "Path contains null bytes"):
                get_safe_path(tmpdir, "file.txt\0secret")
            with self.assertRaisesRegex(ValueError, "Path contains null bytes"):
                get_safe_path(tmpdir + "\0", "file.txt")

    def test_get_safe_path_symlink_traversal(self):
        """Should raise ValueError for paths that escape via symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = os.path.join(tmpdir, "base")
            outside = os.path.join(tmpdir, "outside")
            os.makedirs(base)
            os.makedirs(outside)

            # Create a symlink in base pointing to outside
            os.symlink(outside, os.path.join(base, "link"))

            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                get_safe_path(base, "link/secret.txt")

    def test_get_safe_path_lexical_traversal(self):
        """Should raise ValueError for lexical traversal even if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Complex lexical traversal that resolves to outside
            # but might be hard to catch without lexical checks
            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                get_safe_path(tmpdir, "sub/../../outside")

    def test_get_safe_path_symlink_dotdot_bypass(self):
        """Should raise ValueError for symlink followed by .. that escapes base."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = os.path.join(tmpdir, "base")
            outside = os.path.join(tmpdir, "outside")
            os.makedirs(base)
            os.makedirs(outside)

            # base/link -> outside
            os.symlink(outside, os.path.join(base, "link"))

            # link/../outside resolves physically to outside
            # Lexically it resolves to base/outside (if base/link/.. is simplified)
            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                get_safe_path(base, "link/../outside/secret.txt")


if __name__ == "__main__":
    unittest.main()

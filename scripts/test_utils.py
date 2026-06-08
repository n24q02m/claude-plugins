import os
import unittest
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

    def test_sanitize_log_empty(self):
        """Should handle empty string."""
        self.assertEqual(sanitize_log(""), "")

    def test_sanitize_log_mixed(self):
        """Should handle mixed special characters and normal text."""
        self.assertEqual(
            sanitize_log("Error: 100% fail\r\nNext line"),
            "Error: 100%25 fail%0D%0ANext line",
        )

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
        base = "/tmp/base"
        self.assertEqual(get_safe_path(base, "sub/path"), "sub/path")
        self.assertEqual(get_safe_path(base, "./sub/path"), "sub/path")
        # absolute path within base
        self.assertEqual(get_safe_path(base, "/tmp/base/sub/path"), "sub/path")

    def test_get_safe_path_traversal(self):
        """Should raise ValueError for path traversal attempts."""
        base = "/tmp/base"
        with self.assertRaises(ValueError):
            get_safe_path(base, "../traversal")
        with self.assertRaises(ValueError):
            get_safe_path(base, "/etc/passwd")

    def test_get_safe_path_real_paths(self):
        """Should handle real paths and symbolic links via realpath."""
        # Using current directory as a safe base for testing realpath logic
        cwd = os.getcwd()
        self.assertEqual(get_safe_path(cwd, "."), ".")
        with self.assertRaises(ValueError):
            get_safe_path(cwd, "..")


if __name__ == "__main__":
    unittest.main()

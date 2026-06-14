import unittest
import os
import tempfile
from unittest.mock import patch
from utils import sanitize_log, PLUGIN_NAME_PATTERN, get_safe_path, _cached_realpath


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

    @patch("os.path.realpath")
    def test_cached_realpath_optimization(self, mock_realpath):
        """Should cache repeated calls to os.path.realpath for the same path."""
        _cached_realpath.cache_clear()
        self.addCleanup(_cached_realpath.cache_clear)
        mock_realpath.side_effect = lambda x: x

        path = "/test/path"
        _cached_realpath(path)
        _cached_realpath(path)
        _cached_realpath(path)

        mock_realpath.assert_called_once_with(path)

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


if __name__ == "__main__":
    unittest.main()

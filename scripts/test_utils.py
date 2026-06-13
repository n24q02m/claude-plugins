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

    def test_get_safe_path_absolute_inside(self):
        """Should allow absolute paths that resolve inside the base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            real_tmpdir = os.path.realpath(tmpdir)
            inner_path = os.path.join(real_tmpdir, "allowed")
            os.makedirs(inner_path)

            self.assertEqual(get_safe_path(real_tmpdir, inner_path), "allowed")

    def test_get_safe_path_symlinks(self):
        """Should handle symlinks correctly, blocking traversal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            real_tmpdir = os.path.realpath(tmpdir)

            # Internal symlink
            target_dir = os.path.join(real_tmpdir, "target")
            os.makedirs(target_dir)
            link_path = os.path.join(real_tmpdir, "link")
            os.symlink(target_dir, link_path)

            self.assertEqual(get_safe_path(real_tmpdir, "link"), "target")

            # External symlink
            with tempfile.TemporaryDirectory() as external_dir:
                real_external = os.path.realpath(external_dir)
                external_link = os.path.join(real_tmpdir, "external_link")
                os.symlink(real_external, external_link)

                with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                    get_safe_path(real_tmpdir, "external_link")

    def test_get_safe_path_complex_dots(self):
        """Should handle complex paths with multiple dot segments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            real_tmpdir = os.path.realpath(tmpdir)
            os.makedirs(os.path.join(real_tmpdir, "a/b/c"))

            self.assertEqual(get_safe_path(real_tmpdir, "a/./b/../b/c"), "a/b/c")

            with self.assertRaisesRegex(ValueError, "Path traversal detected"):
                get_safe_path(real_tmpdir, "a/b/../../..")


if __name__ == "__main__":
    unittest.main()

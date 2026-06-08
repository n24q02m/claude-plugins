import os
import tempfile
import unittest
from unittest.mock import patch
import utils
from utils import sanitize_log, PLUGIN_NAME_PATTERN, get_safe_path


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.real_project_root = utils.PROJECT_ROOT
        utils.PROJECT_ROOT = self.test_dir

    def tearDown(self):
        utils.PROJECT_ROOT = self.real_project_root
        import shutil

        shutil.rmtree(self.test_dir)

    def test_get_safe_path_valid(self):
        """Should return absolute path for valid subpath."""
        subpath = "plugins/my-plugin"
        expected = os.path.realpath(os.path.join(self.test_dir, subpath))
        os.makedirs(os.path.dirname(expected), exist_ok=True)
        # We don't necessarily need the file to exist for get_safe_path, but it's good practice
        self.assertEqual(get_safe_path(subpath), expected)

    def test_get_safe_path_traversal(self):
        """Should raise ValueError for path traversal attempts."""
        traversal_paths = [
            "../external",
            "plugins/../../etc/passwd",
            "/etc/passwd",
        ]
        for path in traversal_paths:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    get_safe_path(path)

    def test_get_safe_path_symlink_traversal(self):
        """Should raise ValueError for symlinks pointing outside base_dir."""
        external_dir = tempfile.mkdtemp()
        try:
            malicious_link = os.path.join(self.test_dir, "malicious")
            os.symlink(external_dir, malicious_link)

            with self.assertRaises(ValueError):
                get_safe_path("malicious/secret.txt")
        finally:
            import shutil

            shutil.rmtree(external_dir)

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


if __name__ == "__main__":
    unittest.main()

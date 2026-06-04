import unittest
from utils import sanitize_log, PLUGIN_NAME_PATTERN


class TestUtils(unittest.TestCase):
    def test_sanitize_log_basic(self):
        self.assertEqual(sanitize_log("hello"), "hello")
        self.assertEqual(sanitize_log(""), "")

    def test_sanitize_log_percent(self):
        self.assertEqual(sanitize_log("100%"), "100%25")

    def test_sanitize_log_newlines(self):
        self.assertEqual(sanitize_log("line1\nline2"), "line1%0Aline2")
        self.assertEqual(sanitize_log("line1\rline2"), "line1%0Dline2")

    def test_sanitize_log_combined(self):
        self.assertEqual(sanitize_log("%\n\r"), "%25%0A%0D")

    def test_sanitize_log_non_string(self):
        self.assertEqual(sanitize_log(123), "123")
        self.assertEqual(sanitize_log(None), "None")

    def test_plugin_name_pattern_valid(self):
        valid_names = ["my-plugin", "plugin123", "SimpleName", "a-b-c"]
        for name in valid_names:
            with self.subTest(name=name):
                # match() checks from the beginning, and $ matches newline at end
                self.assertTrue(PLUGIN_NAME_PATTERN.match(name))

    def test_plugin_name_pattern_invalid(self):
        # Note: "plugin\n" is technically matched by ^...$ because $ matches before \n at end of string
        invalid_names = ["my_plugin", "plugin!", " name", "", "plugin\nmore"]
        for name in invalid_names:
            with self.subTest(name=name):
                self.assertFalse(PLUGIN_NAME_PATTERN.match(name))


if __name__ == "__main__":
    unittest.main()

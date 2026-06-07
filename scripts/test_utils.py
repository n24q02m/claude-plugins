import unittest
import os
import tempfile
import shutil
from scripts.utils import get_safe_path, PROJECT_ROOT


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = os.path.join(self.test_dir, "base")
        os.makedirs(self.base_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_safe_path_valid(self):
        # Normal relative path
        target = os.path.join(self.base_dir, "plugins/my-plugin")
        os.makedirs(target)
        res = get_safe_path("plugins/my-plugin", base_dir=self.base_dir)
        self.assertEqual(res, os.path.realpath(target))

    def test_get_safe_path_traversal_dots(self):
        # Path traversal using ..
        with self.assertRaises(ValueError):
            get_safe_path("../../../etc/passwd", base_dir=self.base_dir)

    def test_get_safe_path_absolute(self):
        # Absolute path outside base
        with self.assertRaises(ValueError):
            get_safe_path("/etc/passwd", base_dir=self.base_dir)

    def test_get_safe_path_symlink_traversal(self):
        # Symlink pointing outside base
        secret_file = os.path.join(self.test_dir, "secret.txt")
        with open(secret_file, "w") as f:
            f.write("secret")

        malicious_link = os.path.join(self.base_dir, "malicious_link")
        os.symlink(secret_file, malicious_link)

        with self.assertRaises(ValueError):
            get_safe_path("malicious_link", base_dir=self.base_dir)

    def test_project_root_constant(self):
        # Ensure PROJECT_ROOT is correctly identified
        # scripts/utils.py is in <root>/scripts/utils.py
        # PROJECT_ROOT should be <root>
        self.assertTrue(os.path.isdir(PROJECT_ROOT))
        self.assertTrue(
            os.path.exists(os.path.join(PROJECT_ROOT, "scripts", "utils.py"))
        )


if __name__ == "__main__":
    unittest.main()

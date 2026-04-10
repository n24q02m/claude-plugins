import unittest
import os
import sys
import shutil
import tempfile

# Add plugins directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins")))
from mcp_utils import is_configured

class TestMcpUtils(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.old_environ = os.environ.copy()
        # Mock HOME to our temp dir
        os.environ["HOME"] = self.tmp_dir
        # Clear other relevant env vars
        for key in ["LOCALAPPDATA", "APPDATA", "TEST_KEY"]:
            if key in os.environ:
                del os.environ[key]

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_environ)
        shutil.rmtree(self.tmp_dir)

    def test_configured_via_env(self):
        self.assertFalse(is_configured(["TEST_KEY"]))
        os.environ["TEST_KEY"] = "present"
        self.assertTrue(is_configured(["TEST_KEY"]))

    def test_configured_via_home_config(self):
        config_dir = os.path.join(self.tmp_dir, ".config", "mcp")
        os.makedirs(config_dir)
        config_file = os.path.join(config_dir, "config.enc")

        self.assertFalse(is_configured(["TEST_KEY"]))
        with open(config_file, "w") as f:
            f.write("data")
        self.assertTrue(is_configured(["TEST_KEY"]))

    def test_configured_via_localappdata(self):
        os.environ["LOCALAPPDATA"] = self.tmp_dir
        config_dir = os.path.join(self.tmp_dir, "mcp")
        os.makedirs(config_dir)
        config_file = os.path.join(config_dir, "config.enc")

        self.assertFalse(is_configured(["TEST_KEY"]))
        with open(config_file, "w") as f:
            f.write("data")
        self.assertTrue(is_configured(["TEST_KEY"]))

    def test_configured_via_appdata(self):
        os.environ["APPDATA"] = self.tmp_dir
        config_dir = os.path.join(self.tmp_dir, "mcp", "Config")
        os.makedirs(config_dir)
        config_file = os.path.join(config_dir, "config.enc")

        self.assertFalse(is_configured(["TEST_KEY"]))
        with open(config_file, "w") as f:
            f.write("data")
        self.assertTrue(is_configured(["TEST_KEY"]))

if __name__ == "__main__":
    unittest.main()

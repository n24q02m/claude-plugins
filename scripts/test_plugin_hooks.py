import unittest
import os
import tempfile
import shutil
import subprocess
import json

class TestHooksLogic(unittest.TestCase):
    def setUp(self):
        self.hooks = [
            "plugins/better-code-review-graph/hooks/check-credentials.py",
            "plugins/wet-mcp/hooks/check-credentials.py",
            "plugins/mnemo-mcp/hooks/check-credentials.py"
        ]
        self.temp_dir = tempfile.mkdtemp()
        self.old_environ = os.environ.copy()
        os.environ.clear()
        # Restore basics needed for subprocess and python
        for k in ['PATH', 'PYTHONPATH', 'USER']:
            if k in self.old_environ:
                os.environ[k] = self.old_environ[k]
        os.environ['HOME'] = self.temp_dir

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_environ)
        shutil.rmtree(self.temp_dir)

    def run_hook(self, hook_path, tool_name="test_tool"):
        proc = subprocess.Popen(
            ['python3', hook_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(input=json.dumps({"tool_name": tool_name}))
        return proc.returncode, stdout, stderr

    def test_no_config(self):
        for hook in self.hooks:
            rc, stdout, stderr = self.run_hook(hook)
            self.assertEqual(rc, 0)
            self.assertIn("Note:", stdout)

    def test_env_config(self):
        os.environ["OPENAI_API_KEY"] = "test"
        for hook in self.hooks:
            rc, stdout, stderr = self.run_hook(hook)
            self.assertEqual(rc, 0)
            self.assertEqual(stdout.strip(), "", f"Hook {hook} failed to detect ENV config")
        del os.environ["OPENAI_API_KEY"]

    def test_file_config(self):
        # Create a dummy config file in HOME
        config_dir = os.path.join(self.temp_dir, ".config", "mcp")
        os.makedirs(config_dir)
        config_file = os.path.join(config_dir, "config.enc")
        with open(config_file, "w") as f:
            f.write("dummy")

        for hook in self.hooks:
            rc, stdout, stderr = self.run_hook(hook)
            self.assertEqual(rc, 0)
            self.assertEqual(stdout.strip(), "", f"Hook {hook} failed to detect FILE config at {config_file}")

    def test_exempt_suffix(self):
        for hook in self.hooks:
            rc, stdout, stderr = self.run_hook(hook, tool_name="some__setup")
            self.assertEqual(rc, 0)
            self.assertEqual(stdout.strip(), "", f"Hook {hook} should be exempt for __setup")

if __name__ == '__main__':
    unittest.main()

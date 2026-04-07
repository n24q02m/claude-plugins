import unittest
import json
import os
import shutil
import tempfile
from validate_marketplace import validate_marketplace

class TestValidateMarketplace(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create .claude-plugin directory
        os.makedirs(".claude-plugin")

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def create_marketplace(self, plugins):
        data = {
            "name": "Test Marketplace",
            "metadata": {},
            "owner": "test",
            "plugins": plugins
        }
        with open(".claude-plugin/marketplace.json", "w") as f:
            json.dump(data, f)

    def create_plugin(self, name, source, plugin_json=None, gemini_ext=None, skills=None):
        plugin_dir = source.lstrip("./")
        os.makedirs(os.path.join(plugin_dir, ".claude-plugin"), exist_ok=True)

        if plugin_json:
            with open(os.path.join(plugin_dir, ".claude-plugin", "plugin.json"), "w") as f:
                json.dump(plugin_json, f)

        if gemini_ext:
            with open(os.path.join(plugin_dir, "gemini-extension.json"), "w") as f:
                json.dump(gemini_ext, f)

        if skills:
            skills_dir = os.path.join(plugin_dir, "skills")
            for skill_name, content in skills.items():
                skill_path = os.path.join(skills_dir, skill_name)
                os.makedirs(skill_path, exist_ok=True)
                with open(os.path.join(skill_path, "SKILL.md"), "w") as f:
                    f.write(content)

    def test_valid_marketplace(self):
        self.create_marketplace([{"name": "p1", "source": "./p1"}])
        self.create_plugin("p1", "./p1",
                          plugin_json={"name": "p1", "description": "d", "mcpServers": []})

        # Should not raise or exit
        try:
            validate_marketplace()
        except SystemExit:
            self.fail("validate_marketplace exited unexpectedly")

    def test_missing_plugin_json(self):
        self.create_marketplace([{"name": "p1", "source": "./p1"}])
        # Don't create plugin.json

        with self.assertRaises(SystemExit) as cm:
            validate_marketplace()
        self.assertEqual(cm.exception.code, 1)

    def test_invalid_skill(self):
        self.create_marketplace([{"name": "p1", "source": "./p1"}])
        self.create_plugin("p1", "./p1",
                          plugin_json={"name": "p1", "description": "d", "mcpServers": []},
                          skills={"s1": "too short"})

        with self.assertRaises(SystemExit) as cm:
            validate_marketplace()
        self.assertEqual(cm.exception.code, 1)

if __name__ == "__main__":
    unittest.main()

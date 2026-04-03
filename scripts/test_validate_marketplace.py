#!/usr/bin/env python3
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
        os.makedirs(".claude-plugin")

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def create_marketplace(self, plugins):
        marketplace = {
            "name": "test-marketplace",
            "metadata": {"description": "test", "version": "1.0.0", "pluginRoot": "./plugins"},
            "owner": {"name": "test", "email": "test@example.com"},
            "plugins": plugins
        }
        with open(".claude-plugin/marketplace.json", "w") as f:
            json.dump(marketplace, f)

    def create_plugin(self, name, plugin_json=True, gemini_json=True, skill=True):
        plugin_dir = f"plugins/{name}"
        os.makedirs(f"{plugin_dir}/.claude-plugin")
        if plugin_json:
            with open(f"{plugin_dir}/.claude-plugin/plugin.json", "w") as f:
                json.dump({"name": name, "description": "test", "mcpServers": []}, f)
        if gemini_json:
            with open(f"{plugin_dir}/gemini-extension.json", "w") as f:
                json.dump({"version": "1.0.0"}, f)
        if skill:
            os.makedirs(f"{plugin_dir}/skills/test-skill")
            with open(f"{plugin_dir}/skills/test-skill/SKILL.md", "w") as f:
                f.write("---\ntitle: test\n---\nThis is a long enough content for the test skill validation.")

    def test_valid_marketplace(self):
        self.create_marketplace([{"name": "test-plugin", "source": "./plugins/test-plugin"}])
        self.create_plugin("test-plugin")
        # Should not raise any exception
        validate_marketplace()

    def test_missing_plugin_json(self):
        self.create_marketplace([{"name": "test-plugin", "source": "./plugins/test-plugin"}])
        os.makedirs("plugins/test-plugin/.claude-plugin")
        # Gemeni extension is still needed or it will fail on that first if pjson doesn't exist
        with self.assertRaises(SystemExit):
             validate_marketplace()

    def test_invalid_skill_no_frontmatter(self):
        self.create_marketplace([{"name": "test-plugin", "source": "./plugins/test-plugin"}])
        self.create_plugin("test-plugin", skill=False)
        os.makedirs("plugins/test-plugin/skills/bad-skill")
        with open("plugins/test-plugin/skills/bad-skill/SKILL.md", "w") as f:
            f.write("No frontmatter here.")
        with self.assertRaises(SystemExit):
            validate_marketplace()

if __name__ == "__main__":
    unittest.main()

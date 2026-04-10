#!/usr/bin/env python3
"""Unit tests for validate_marketplace script."""

import unittest
import os
import json
import shutil
import tempfile
from unittest.mock import patch, MagicMock
import validate_marketplace

class TestValidateMarketplace(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create minimal structure
        os.makedirs(".claude-plugin")
        self.marketplace_path = ".claude-plugin/marketplace.json"

        self.valid_marketplace = {
            "name": "Test Marketplace",
            "metadata": {},
            "owner": "test-owner",
            "plugins": [
                {
                    "name": "test-plugin",
                    "source": "./plugins/test-plugin"
                }
            ]
        }

        with open(self.marketplace_path, 'w') as f:
            json.dump(self.valid_marketplace, f)

        os.makedirs("plugins/test-plugin/.claude-plugin")
        self.plugin_json_path = "plugins/test-plugin/.claude-plugin/plugin.json"
        self.valid_plugin = {
            "name": "test-plugin",
            "description": "A test plugin",
            "mcpServers": []
        }
        with open(self.plugin_json_path, 'w') as f:
            json.dump(self.valid_plugin, f)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_valid_marketplace(self):
        """Should pass for a valid marketplace and plugin."""
        with patch('sys.exit') as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_not_called()

    def test_missing_required_field(self):
        """Should fail if a required field is missing in marketplace.json."""
        del self.valid_marketplace["name"]
        with open(self.marketplace_path, 'w') as f:
            json.dump(self.valid_marketplace, f)

        with patch('sys.exit') as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_missing_plugin_json(self):
        """Should fail if plugin.json is missing."""
        os.remove(self.plugin_json_path)

        with patch('sys.exit') as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_invalid_plugin_json(self):
        """Should fail if plugin.json is missing required fields."""
        del self.valid_plugin["description"]
        with open(self.plugin_json_path, 'w') as f:
            json.dump(self.valid_plugin, f)

        with patch('sys.exit') as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_skill_missing_frontmatter(self):
        """Should fail if a skill SKILL.md is missing frontmatter."""
        skill_dir = "plugins/test-plugin/skills/test-skill"
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), 'w') as f:
            f.write("No frontmatter here.")

        with patch('sys.exit') as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_skill_too_short(self):
        """Should fail if a skill SKILL.md is too short."""
        skill_dir = "plugins/test-plugin/skills/test-skill"
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), 'w') as f:
            f.write("---\nshort")

        with patch('sys.exit') as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_missing_source(self):
        """Should fail if a plugin is missing the source field."""
        del self.valid_marketplace["plugins"][0]["source"]
        with open(self.marketplace_path, "w") as f:
            json.dump(self.valid_marketplace, f)

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

if __name__ == '__main__':
    unittest.main()

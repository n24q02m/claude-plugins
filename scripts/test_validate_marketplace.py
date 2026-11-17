#!/usr/bin/env python3
"""Unit tests for validate_marketplace script."""

import contextlib
import io
import unittest
import os
import json
import runpy
import shutil
import tempfile
from unittest.mock import patch
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
            "plugins": [{"name": "test-plugin", "source": "./plugins/test-plugin"}],
        }

        with open(self.marketplace_path, "w") as f:
            json.dump(self.valid_marketplace, f)

        os.makedirs("plugins/test-plugin/.claude-plugin")
        self.plugin_json_path = "plugins/test-plugin/.claude-plugin/plugin.json"
        self.valid_plugin = {
            "name": "test-plugin",
            "description": "A test plugin",
            "mcpServers": [],
        }
        with open(self.plugin_json_path, "w") as f:
            json.dump(self.valid_plugin, f)

    def tearDown(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_valid_marketplace(self):
        """Should pass for a valid marketplace and plugin."""
        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_not_called()

    def test_missing_required_field(self):
        """Should fail if a required field is missing in marketplace.json."""
        del self.valid_marketplace["name"]
        with open(self.marketplace_path, "w") as f:
            json.dump(self.valid_marketplace, f)

        with patch("sys.exit") as mock_exit:
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

    def test_path_traversal_source(self):
        """Should fail if a plugin has a path traversal in source."""
        self.valid_marketplace["plugins"][0]["source"] = "../../../etc/passwd"
        with open(self.marketplace_path, "w") as f:
            json.dump(self.valid_marketplace, f)

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_invalid_name(self):
        """Should fail if a plugin has an invalid name format."""
        self.valid_marketplace["plugins"][0]["name"] = "invalid_name!"
        with open(self.marketplace_path, "w") as f:
            json.dump(self.valid_marketplace, f)

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_non_string_name(self):
        """Should fail if a plugin name is not a string."""
        self.valid_marketplace["plugins"][0]["name"] = 123
        with open(self.marketplace_path, "w") as f:
            json.dump(self.valid_marketplace, f)

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_non_string_source(self):
        """Should fail if a plugin source is not a string."""
        self.valid_marketplace["plugins"][0]["source"] = 123
        with open(self.marketplace_path, "w") as f:
            json.dump(self.valid_marketplace, f)

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_missing_plugin_json(self):
        """Should fail if plugin.json is missing."""
        os.remove(self.plugin_json_path)

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_invalid_plugin_json(self):
        """Should fail if plugin.json is missing required fields."""
        del self.valid_plugin["description"]
        with open(self.plugin_json_path, "w") as f:
            json.dump(self.valid_plugin, f)

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_skill_missing_frontmatter(self):
        """Should fail if a skill SKILL.md is missing frontmatter."""
        skill_dir = "plugins/test-plugin/skills/test-skill"
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("No frontmatter here.")

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_skill_too_short(self):
        """Should fail if a skill SKILL.md is too short."""
        skill_dir = "plugins/test-plugin/skills/test-skill"
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("---\nshort")

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_gemini_extension_missing_version(self):
        """Should fail if gemini-extension.json is missing version."""
        gext_path = "plugins/test-plugin/gemini-extension.json"
        with open(gext_path, "w") as f:
            json.dump({"foo": "bar"}, f)

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_gemini_extension_invalid_json(self):
        """Should fail if gemini-extension.json is invalid JSON."""
        gext_path = "plugins/test-plugin/gemini-extension.json"
        with open(gext_path, "w") as f:
            f.write("invalid json")

        with patch("sys.exit") as mock_exit:
            validate_marketplace.validate_marketplace()
            mock_exit.assert_called_with(1)

    def test_load_marketplace_failure(self):
        """Should fail if marketplace.json cannot be loaded."""
        with (
            patch("builtins.open", side_effect=Exception("Read error")),
            patch("sys.exit", side_effect=SystemExit(1)) as mock_exit,
            patch("builtins.print") as mock_print,
        ):
            with self.assertRaises(SystemExit) as cm:
                validate_marketplace.validate_marketplace()
            self.assertEqual(cm.exception.code, 1)
            mock_print.assert_any_call(
                "::error ::Failed to load marketplace.json: Read error"
            )
            mock_exit.assert_called()

    def _run(self):
        """Run the validator; return (exit code or None, printed lines)."""
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            try:
                validate_marketplace.validate_marketplace()
                code = None
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue().splitlines()

    def _write_marketplace(self):
        with open(self.marketplace_path, "w") as f:
            json.dump(self.valid_marketplace, f)

    def test_valid_optional_files_pass(self):
        """A versioned gemini-extension.json and well-formed skills add no error;
        stray files and folders without SKILL.md under skills/ are ignored."""
        plugin = "plugins/test-plugin"
        with open(os.path.join(plugin, "gemini-extension.json"), "w") as f:
            json.dump({"version": "1.0.0"}, f)
        os.makedirs(os.path.join(plugin, "skills", "good-skill"))
        with open(os.path.join(plugin, "skills", "good-skill", "SKILL.md"), "w") as f:
            f.write("---\nname: good-skill\ndescription: a skill long enough to pass\n---\n")
        os.makedirs(os.path.join(plugin, "skills", "assets-only"))
        with open(os.path.join(plugin, "skills", "README.txt"), "w") as f:
            f.write("not a skill")

        code, lines = self._run()

        self.assertIsNone(code)
        self.assertEqual(lines, ["All 1 plugins validated successfully"])

    def test_unparseable_plugin_json_is_reported(self):
        with open(self.plugin_json_path, "w") as f:
            f.write("{not json")

        code, lines = self._run()

        self.assertEqual(code, 1)
        self.assertTrue(
            any("test-plugin: Failed to parse" in line for line in lines), lines
        )

    def test_unreadable_skill_file_is_reported(self):
        skill_dir = "plugins/test-plugin/skills/test-skill"
        os.makedirs(skill_dir)
        with open(os.path.join(skill_dir, "SKILL.md"), "wb") as f:
            f.write(b"---\n\xff\xfe not utf-8\n")

        code, lines = self._run()

        self.assertEqual(code, 1)
        self.assertTrue(
            any("skills/test-skill: Failed to read SKILL.md" in line for line in lines),
            lines,
        )

    def test_plugin_without_name_is_reported_as_unknown(self):
        errors = validate_marketplace._validate_plugin(
            {"source": "./plugins/absent"}, os.getcwd()
        )
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("Unknown: missing"), errors)

    def test_missing_plugins_field_is_reported(self):
        del self.valid_marketplace["plugins"]
        self._write_marketplace()

        code, lines = self._run()

        self.assertEqual(code, 1)
        self.assertIn("::error ::marketplace.json: Missing field: plugins", lines)

    def test_empty_plugin_list_is_reported(self):
        self.valid_marketplace["plugins"] = []
        self._write_marketplace()

        code, lines = self._run()

        self.assertEqual(code, 1)
        self.assertIn("::error ::marketplace.json: No plugins defined", lines)

    def test_runs_as_a_script(self):
        script = os.path.join(os.path.dirname(validate_marketplace.__file__), "validate_marketplace.py")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            runpy.run_path(script, run_name="__main__")
        self.assertIn("All 1 plugins validated successfully", out.getvalue())


if __name__ == "__main__":
    unittest.main()

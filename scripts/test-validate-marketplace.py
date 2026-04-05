import os
import json
import shutil
import tempfile
import subprocess
import sys

def test_validation():
    # Create a temporary directory for the mock environment
    mock_root = tempfile.mkdtemp()
    try:
        # 1. Test valid case
        os.makedirs(os.path.join(mock_root, ".claude-plugin"))
        plugin_dir = os.path.join(mock_root, "plugins", "test-plugin")
        os.makedirs(os.path.join(plugin_dir, ".claude-plugin"))
        skill_dir = os.path.join(plugin_dir, "skills", "test-skill")
        os.makedirs(skill_dir)

        # Valid marketplace.json
        with open(os.path.join(mock_root, ".claude-plugin", "marketplace.json"), "w") as f:
            json.dump({
                "name": "Test Marketplace",
                "metadata": {},
                "owner": "test",
                "plugins": [{"name": "test-plugin", "source": "./plugins/test-plugin"}]
            }, f)

        # Valid plugin.json
        with open(os.path.join(plugin_dir, ".claude-plugin", "plugin.json"), "w") as f:
            json.dump({
                "name": "test-plugin",
                "description": "A test plugin",
                "mcpServers": []
            }, f)

        # Valid SKILL.md
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("---\ntitle: Test Skill\n---\n" + "x" * 60)

        # Run validation
        print("Running validation on valid mock...")
        script_path = os.path.abspath("scripts/validate_marketplace.py")
        subprocess.check_call([sys.executable, script_path], cwd=mock_root)
        print("Success: Valid mock passed validation.")

        # 2. Test missing field in marketplace.json
        print("Checking failure on missing 'owner' field...")
        with open(os.path.join(mock_root, ".claude-plugin", "marketplace.json"), "w") as f:
            json.dump({
                "name": "Test Marketplace",
                "metadata": {},
                "plugins": []
            }, f)

        try:
            subprocess.check_call([sys.executable, script_path], cwd=mock_root, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            print("Error: Validation should have failed for missing 'owner' field")
            sys.exit(1)
        except subprocess.CalledProcessError:
            print("Success: Validation failed as expected.")

        # 3. Test too short SKILL.md
        print("Checking failure on short SKILL.md...")
        with open(os.path.join(mock_root, ".claude-plugin", "marketplace.json"), "w") as f:
            json.dump({
                "name": "Test Marketplace",
                "metadata": {},
                "owner": "test",
                "plugins": [{"name": "test-plugin", "source": "./plugins/test-plugin"}]
            }, f)
        with open(os.path.join(skill_dir, "SKILL.md"), "w") as f:
            f.write("---\ntitle: Short\n---\nshort")

        process = subprocess.run([sys.executable, script_path], cwd=mock_root, capture_output=True, text=True)
        if "SKILL.md too short" in process.stdout:
            print("Success: Caught short SKILL.md.")
        else:
            print("Error: Validation should have caught short SKILL.md")
            print("Output was:", process.stdout)
            sys.exit(1)

        print("All tests passed!")
    finally:
        shutil.rmtree(mock_root)

if __name__ == "__main__":
    test_validation()

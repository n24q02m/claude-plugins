import re

with open("scripts/check_version_freshness.py") as f:
    text = f.read()

# Replace test_check_plugin_valid_name mock
text = re.sub(
    r'    if os.path.exists\(pjson_path\):\n        try:\n            with open\(pjson_path\) as f:\n                pdata = json.load\(f\)\n            marketplace_ver = pdata.get\("version", "unknown"\)\n        except \(OSError, json.JSONDecodeError\) as e:\n            print\(f"::warning ::\{sanitize_log\(f\'Failed to parse \{pjson_path\}: \{e\}\)\}"\)\n    elif os.path.exists\(gext_path\):\n        try:\n            with open\(gext_path\) as f:\n                gdata = json.load\(f\)\n            marketplace_ver = gdata.get\("version", "unknown"\)\n        except \(OSError, json.JSONDecodeError\) as e:\n            print\(f"::warning ::\{sanitize_log\(f\'Failed to parse \{gext_path\}: \{e\}\)\}"\)',
    r'''    try:
        with open(pjson_path) as f:
            pdata = json.load(f)
        marketplace_ver = pdata.get("version", "unknown")
    except FileNotFoundError:
        try:
            with open(gext_path) as f:
                gdata = json.load(f)
            marketplace_ver = gdata.get("version", "unknown")
        except FileNotFoundError:
            pass
        except (OSError, json.JSONDecodeError) as e:
            print(f"::warning ::{sanitize_log(f'Failed to parse {gext_path}: {e}')}")
    except (OSError, json.JSONDecodeError) as e:
        print(f"::warning ::{sanitize_log(f'Failed to parse {pjson_path}: {e}')}")''',
    text
)

with open("scripts/check_version_freshness.py", "w") as f:
    f.write(text)

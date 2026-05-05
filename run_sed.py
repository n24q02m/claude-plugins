with open("scripts/check_version_freshness.py", "r") as f:
    text = f.read()

import re

search = """    marketplace_ver = "unknown"
    if os.path.exists(pjson_path):
        try:
            with open(pjson_path) as f:
                pdata = json.load(f)
            marketplace_ver = pdata.get("version", "unknown")
        except (OSError, json.JSONDecodeError) as e:
            print(f"::warning ::{sanitize_log(f'Failed to parse {pjson_path}: {e}')}")
    elif os.path.exists(gext_path):
        try:
            with open(gext_path) as f:
                gdata = json.load(f)
            marketplace_ver = gdata.get("version", "unknown")
        except (OSError, json.JSONDecodeError) as e:
            print(f"::warning ::{sanitize_log(f'Failed to parse {gext_path}: {e}')}")"""

replace = """    marketplace_ver = "unknown"
    try:
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
        print(f"::warning ::{sanitize_log(f'Failed to parse {pjson_path}: {e}')}")"""

if search in text:
    print("Found search block in check_version_freshness.py")
else:
    print("Could not find search block in check_version_freshness.py")

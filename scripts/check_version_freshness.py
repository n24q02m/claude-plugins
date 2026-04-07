"""Check marketplace plugin versions against latest GitHub releases."""

import concurrent.futures
import json
import os
import subprocess

def get_ver(plugin_dir):
    """Get version from plugin.json or gemini-extension.json."""
    for path in [os.path.join(plugin_dir, ".claude-plugin", "plugin.json"),
                 os.path.join(plugin_dir, "gemini-extension.json")]:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    v = json.load(f).get("version")
                    if v: return v
            except Exception: pass
    return "unknown"

def check_plugin(plugin):
    name, source = plugin["name"], plugin["source"].lstrip("./")
    plugin_dir = os.path.normpath(source)
    v = get_ver(plugin_dir)

    if v == "unknown" and not any(os.path.exists(os.path.join(plugin_dir, f))
                                 for f in [".claude-plugin/plugin.json", "gemini-extension.json"]):
        v = "missing"

    try:
        res = subprocess.run(["gh", "release", "view", "--repo", f"n24q02m/{name}",
                             "--json", "tagName", "-q", ".tagName"],
                            capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            latest = res.stdout.strip().lstrip("v")
            return {"name": name, "v": v, "latest": latest, "status": "stale" if v != latest else "ok"}
        return {"name": name, "v": v, "status": "no-release"}
    except FileNotFoundError:
        return {"name": name, "v": v, "status": "error", "err": "gh CLI missing"}
    except Exception as e:
        return {"name": name, "v": v, "status": "error", "err": str(e)}

def main():
    try:
        with open(".claude-plugin/marketplace.json") as f:
            plugins = json.load(f)["plugins"]
    except Exception as e:
        print(f"::error ::Marketplace load failed: {e}"); return

    stale = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as exe:
        for res in [f.result() for f in [exe.submit(check_plugin, p) for p in plugins]]:
            name, v, status = res["name"], res["v"], res["status"]
            if status == "stale":
                stale.append(name)
                print(f"::warning ::{name} stale: {v} -> {res['latest']}")
            elif status == "ok":
                print(f"{name}: up-to-date ({v})")
            elif status == "error":
                print(f"::error ::{name}: {res['err']} ({v})")
            else:
                print(f"{name}: {status} ({v})")

    if stale: print(f"\n{len(stale)} plugin(s) need sync")
    else: print("\nAll plugins up-to-date")

if __name__ == "__main__":
    main()

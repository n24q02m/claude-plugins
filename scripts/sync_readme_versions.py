import os
import re
import urllib.request
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')

REPOS = [
    "wet-mcp",
    "mnemo-mcp",
    "better-notion-mcp",
    "better-email-mcp",
    "better-telegram-mcp",
    "better-godot-mcp",
    "better-code-review-graph"
]

def get_latest_release(repo):
    url = f"https://api.github.com/repos/n24q02m/{repo}/releases/latest"
    req = urllib.request.Request(url)
    
    token = os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
        
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data.get("tag_name", "").lstrip("v")
    except Exception as e:
        logging.warning(f"Could not fetch release for {repo}: {e}")
        return "-"

def update_readme():
    versions = {}
    for repo in REPOS:
        v = get_latest_release(repo)
        versions[repo] = v
        logging.info(f"Found {repo}: {v}")

    readme_path = "README.md"
    if not os.path.exists(readme_path):
        logging.error("README.md not found")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    # The table format is:
    # | Plugin | Category | Description | Env Vars |
    # |--------|----------|-------------|----------|
    # | **wet-mcp** | Research | ...
    # We want to change the header to include Version if not there, or update the existing.
    
    lines = content.split('\n')
    out_lines = []
    
    in_table = False
    has_version_column = False
    
    for line in lines:
        if line.startswith("| Plugin | Category |"):
            line = line.replace("| Plugin | Category |", "| Plugin | Version | Category |")
            has_version_column = False
            in_table = True
            out_lines.append(line)
            continue
            
        if line.startswith("| Plugin | Version | Category |"):
            has_version_column = True
            in_table = True
            out_lines.append(line)
            continue
            
        if in_table and line.startswith("|---"):
            if not has_version_column:
                # Need to add separator for version
                line = line.replace("|--------|----------|", "|--------|---------|----------|")
            out_lines.append(line)
            continue
            
        if in_table and line.startswith("| **"):
            # It's a plugin row
            match = re.match(r"\| \*\*([^*]+)\*\* \|", line)
            if match:
                repo = match.group(1)
                v = versions.get(repo, "-")
                if has_version_column:
                    parts = line.split('|')
                    if len(parts) > 3:
                        parts[2] = f" `{v}` " if v != "-" else " - "
                        line = "|".join(parts)
                else:
                    parts = line.split('|')
                    parts.insert(2, f" `{v}` " if v != "-" else " - ")
                    line = "|".join(parts)
            out_lines.append(line)
            continue
            
        # If we see a blank line, table might be over
        if in_table and line.strip() == "":
            in_table = False
            
        out_lines.append(line)

    new_content = "\n".join(out_lines)
    
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    logging.info("README.md updated.")

if __name__ == "__main__":
    update_readme()

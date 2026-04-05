#!/bin/bash
# Sync plugin configs, skills, and hooks from source repos
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-$(dirname "$SCRIPT_DIR")}"
REPOS_DIR="${REPOS_DIR:-$HOME/projects}"

# O(1) memory directory check using native bash globbing with early-return loop.
# Avoids both subshell overhead (find|head) and O(N) array allocation.
has_files() {
  local dir="$1"
  shopt -s nullglob dotglob
  for _ in "$dir"/*; do
    shopt -u nullglob dotglob
    return 0
  done
  shopt -u nullglob dotglob
  return 1
}

# Sync a file or directory from source to destination
sync_item() {
  local item_path="$1"
  if [ -f "$src/$item_path" ]; then
    mkdir -p "$(dirname "$dst/$item_path")"
    cp "$src/$item_path" "$dst/$item_path"
  elif [ -d "$src/$item_path" ] && has_files "$src/$item_path"; then
    rm -rf "$dst/$item_path"
    mkdir -p "$(dirname "$dst/$item_path")"
    cp -r "$src/$item_path" "$dst/$item_path"
  fi
}

PLUGINS=(wet-mcp mnemo-mcp better-telegram-mcp better-code-review-graph better-notion-mcp better-email-mcp better-godot-mcp)

sync_plugins() {
  for repo in "${PLUGINS[@]}"; do
    src="$REPOS_DIR/$repo"
    dst="$ROOT/plugins/$repo"

    if [ ! -d "$src" ]; then
      echo "SKIP $repo (not found at $src)"
      continue
    fi

    # Sync configuration files
    sync_item ".claude-plugin/plugin.json"
    sync_item "gemini-extension.json"

    # Sync skills and hooks
    sync_item "skills"
    sync_item "hooks"

    echo "OK $repo"
  done

  echo "Sync complete."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  sync_plugins
fi

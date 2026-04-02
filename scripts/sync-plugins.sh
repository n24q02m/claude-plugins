#!/bin/bash
# Sync plugin configs, skills, and hooks from source repos
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
REPOS_DIR="${REPOS_DIR:-$HOME/projects}"

# Faster directory check using native bash globbing instead of subshells + find
# Using O(1) memory efficiency approach as recommended
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

# Sync a directory from source to destination if it contains files
sync_dir() {
  local dir_name="$1"
  if [ -d "$src/$dir_name" ] && has_files "$src/$dir_name"; then
    rm -rf "$dst/$dir_name"
    cp -r "$src/$dir_name" "$dst/$dir_name"
  fi
}

PLUGINS=(wet-mcp mnemo-mcp better-telegram-mcp better-code-review-graph better-notion-mcp better-email-mcp better-godot-mcp)

for repo in "${PLUGINS[@]}"; do
  src="$REPOS_DIR/$repo"
  dst="$ROOT/plugins/$repo"

  if [ ! -d "$src" ]; then
    echo "SKIP $repo (not found at $src)"
    continue
  fi

  # Sync plugin.json
  if [ -f "$src/.claude-plugin/plugin.json" ]; then
    mkdir -p "$dst/.claude-plugin"
    cp "$src/.claude-plugin/plugin.json" "$dst/.claude-plugin/plugin.json"
  fi

  # Sync skills and hooks
  sync_dir "skills"
  sync_dir "hooks"

  echo "OK $repo"
done

echo "Sync complete."

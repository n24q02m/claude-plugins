#!/bin/bash
# Sync plugin configs, skills, and hooks from source repos
set -euo pipefail

# Enable globbing options globally for performance and hidden file support
shopt -s nullglob dotglob

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-$(dirname "$SCRIPT_DIR")}"
REPOS_DIR="${REPOS_DIR:-$HOME/projects}"

# O(1) memory directory check using native bash globbing with early-return loop.
# Avoids both subshell overhead (find|head) and O(N) array allocation.
has_files() {
  local dir="$1"
  for _ in "$dir"/*; do
    return 0
  done
  return 1
}

# Sync a single file from source to destination
sync_file() {
  local file_path="$1"
  if [ -f "$src/$file_path" ]; then
    mkdir -p "$(dirname "$dst/$file_path")"
    cp "$src/$file_path" "$dst/$file_path"
  fi
}

# Sync a directory (skills or hooks) from source to destination
sync_dir() {
  local dir_name="$1"
  if [ -d "$src/$dir_name" ] && has_files "$src/$dir_name"; then
    mkdir -p "$dst"
    rm -rf "$dst/$dir_name"
    cp -r "$src/$dir_name" "$dst/$dir_name"
  fi
}

PLUGINS=(wet-mcp mnemo-mcp better-telegram-mcp better-code-review-graph better-notion-mcp better-email-mcp better-godot-mcp)

sync_plugins() {
  for repo in "${PLUGINS[@]}"; do
    src="$REPOS_DIR/$repo"
    dst="$ROOT/plugins/$repo"

    if [ ! -d "$src" ]; then
      printf "%s\n" "SKIP $repo (not found at $src)"
      continue
    fi

    # Sync metadata files
    sync_file ".claude-plugin/plugin.json"
    sync_file "gemini-extension.json"

    # Sync skills and hooks
    sync_dir "skills"
    sync_dir "hooks"

    printf "%s\n" "OK $repo"
  done

  printf "%s\n" "Sync complete."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  sync_plugins
fi

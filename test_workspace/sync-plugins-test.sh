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

# Sync an item (file or directory) from source to destination
sync_item() {
  local item="$1"
  local s="$src/$item"
  local d="$dst/$item"

  if [ -d "$s" ] && has_files "$s"; then
    mkdir -p "$(dirname "$d")"
    rm -rf "$d"
    cp -r "$s" "$d"
    echo "  Synced $item/"
  elif [ -f "$s" ]; then
    mkdir -p "$(dirname "$d")"
    cp "$s" "$d"
    echo "  Synced $item"
  fi
}

PLUGINS=(plugin-a plugin-b)

sync_plugins() {
  for repo in "${PLUGINS[@]}"; do
    src="$REPOS_DIR/$repo"
    dst="$ROOT/plugins/$repo"

    if [ ! -d "$src" ]; then
      echo "SKIP $repo (not found at $src)"
      continue
    fi

    echo "Syncing $repo..."
    sync_item ".claude-plugin/plugin.json"
    sync_item "skills"
    sync_item "hooks"

    echo "OK $repo"
  done

  echo "Sync complete."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  sync_plugins
fi

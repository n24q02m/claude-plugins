#!/bin/bash
# Sync plugin configs, skills, and hooks from source repos
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${ROOT:-$(dirname "$SCRIPT_DIR")}"
REPOS_DIR="${REPOS_DIR:-$HOME/projects}"

# O(1) memory efficiency directory check using native bash globbing
has_files() {
  local dir="$1"
  shopt -s nullglob dotglob
  # shellcheck disable=SC2034
  for _ in "$dir"/*; do
    shopt -u nullglob dotglob
    return 0
  done
  shopt -u nullglob dotglob
  return 1
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

    if ! has_files "$src"; then
      echo "SKIP $repo (empty directory at $src)"
      continue
    fi

    # Ensure destination directory exists
    mkdir -p "$dst"

    # Sync plugin.json
    if [ -f "$src/.claude-plugin/plugin.json" ]; then
      mkdir -p "$dst/.claude-plugin"
      cp "$src/.claude-plugin/plugin.json" "$dst/.claude-plugin/plugin.json"
    fi

    # Sync skills
    if [ -d "$src/skills" ] && has_files "$src/skills"; then
      rm -rf "$dst/skills"
      cp -r "$src/skills" "$dst/skills"
    fi

    # Sync hooks
    if [ -d "$src/hooks" ] && has_files "$src/hooks"; then
      rm -rf "$dst/hooks"
      cp -r "$src/hooks" "$dst/hooks"
    fi

    echo "OK $repo"
  done

  echo "Sync complete."
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  sync_plugins
fi

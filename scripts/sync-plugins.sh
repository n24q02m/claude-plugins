#!/bin/bash
# Sync plugin configs, skills, and hooks from source repos
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
REPOS_DIR="${REPOS_DIR:-$HOME/projects}"

# Faster directory check using native bash globbing instead of subshells + find.
# An early-return loop avoids the secondary O(N) memory allocation of creating
# a massive Bash array if the directory contains thousands of files.
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

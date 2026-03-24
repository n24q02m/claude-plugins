#!/bin/bash
# Sync plugin configs, skills, and hooks from source repos
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$SCRIPT_DIR")"
REPOS_DIR="${REPOS_DIR:-$HOME/projects}"

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
  if [ -d "$src/skills" ] && [ "$(ls -A "$src/skills" 2>/dev/null)" ]; then
    rm -rf "$dst/skills"
    cp -r "$src/skills" "$dst/skills"
  fi

  # Sync hooks
  if [ -d "$src/hooks" ] && [ "$(ls -A "$src/hooks" 2>/dev/null)" ]; then
    rm -rf "$dst/hooks"
    cp -r "$src/hooks" "$dst/hooks"
  fi

  echo "OK $repo"
done

echo "Sync complete."

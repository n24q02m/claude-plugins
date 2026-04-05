#!/bin/bash
set -euo pipefail
source scripts/sync-plugins.sh

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

REPOS_DIR="$tmp/repos"
ROOT="$tmp/root"
mkdir -p "$REPOS_DIR/only-skills/skills"
touch "$REPOS_DIR/only-skills/skills/test.txt"

PLUGINS=("only-skills")
sync_plugins

## 2024-05-15 - [Sync Script Destination Safety]
**Learning:** In `scripts/sync-plugins.sh`, the synchronization of asset directories (e.g., `skills/`, `hooks/`) failed for plugins that did not contain a `plugin.json` file. This is because the `plugin.json` sync step was responsible for creating the `$dst` directory.
**Action:** Ensure that each synchronization step (like `sync_dir`) creates its own destination parent directory using `mkdir -p "$dst"`.

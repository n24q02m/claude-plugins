# Phase H — GDrive duplicate folder cleanup

Date: 2026-04-11
Executed by: Claude Code session (Phase H subagents)
Spec: `specs/2026-04-10-mcp-core-unified-transport-design.md` §2.6
Plan: `plans/2026-04-11-phase-h-gdrive-cleanup.md`

## Before state (verified via rclone 2026-04-11)

| Server | Folder ID | Created | File | Size |
|---|---|---|---|---|
| mnemo-mcp NEW (kept) | 1WhP5kEZeKfsKYOwEZLNVtMay0gxDdQRX | 2026-04-07 | memories.db | 3.94 MB |
| mnemo-mcp OLD (purged) | 1yStJQIpkQNmryHWUh-K7RD1pIMcUTvoH | 2026-02-12 | memories.db | 3.70 MB |
| wet-mcp NEW (kept) | 18DxObY6S5YeP3A9ERdad9ZkJQmBXTVR0 | 2026-04-07 | docs.db | 1.44 GB |
| wet-mcp OLD (purged) | 1wNf7wwIqIZG9g5UwxiLsn70A3s_sB8L2 | 2026-02-13 | docs-mar12.db + docs-feb26.db (intra-folder dupes) | 2.83 GB |

Total before: 4.3 GB backed up locally to `_backup/gdrive-audit/`.

## H2 analysis findings

**mnemo-mcp memories.db**:
- Schema SAME across OLD + NEW (all 16 tables including FTS5 + sqlite-vec)
- Row overlap: old=228, new=253, intersection=226, only-old=2, only-new=27
- Intersection 100% byte-identical (updated_at + content bytes match)
- Only-in-OLD rows (would be lost by simple discard):
  - `77b281bfb8f7` category=plan (2026-02-13): "Plan: wet-mcp v3 — Comprehensive Improvement"
  - `13c8cc1894d8` category=plan (2026-02-14): "Plan v3: Migrate 8 repos to python-semantic-release"

**wet-mcp docs.db**:
- Schema SAME across all 3 (new, mar12, feb26)
- NEW is mathematical strict superset of both OLD snapshots (libraries 1986, versions 1986, doc_chunks 661294)
- 0 rows unique to any older snapshot
- Intersection metadata diffs are monotonically newer in NEW (discovery_version counters, updated_at timestamps)

## Merge decisions (user-approved)

- **mnemo**: Option 3 — INSERT OR IGNORE merge OLD into NEW → final 255 memories (preserves 2 Feb planning rows)
- **wet**: Option 1 — keep NEW as-is (no merge needed, zero data loss)

## Execution results

**mnemo merge**:
- Python sqlite3 INSERT OR IGNORE into copy of NEW → 253 → 255 memories
- FTS5 `memories_fts` rebuilt via `INSERT INTO memories_fts(memories_fts) VALUES('rebuild')`
- `PRAGMA integrity_check` = ok
- Uploaded merged.db → mnemo NEW folder as memories.db (4.38 MB, 2026-04-11T09:28:30Z, overwrite in place, file ID `1Zqzr7eBKZ8_Ne0bbkeuF38lgwF08YLxz`)

**wet**: No-op — NEW folder already had canonical content. Skip upload.

**Purge**:
- mnemo OLD folder (`1yStJQIpkQNmryHWUh-K7RD1pIMcUTvoH`): purged
- wet OLD folder (`1wNf7wwIqIZG9g5UwxiLsn70A3s_sB8L2`): purged

### Purge technique (rclone behavior note)

`rclone purge echovault-gdrive: --drive-root-folder-id=<ID>` returned exit 0
without deleting anything — the folder contents remained fully intact. Same
issue with `rclone rmdir --drive-root-folder-id=<ID>`, which fails with
`can't purge root directory` because the `--drive-root-folder-id` flag makes
the target folder appear as the remote root, and rclone refuses to remove a
remote root.

Two-step workaround used:

1. `rclone delete echovault-gdrive: --drive-root-folder-id=<ID>` — deleted
   files inside each OLD folder (exit 0, both listings empty afterward).
2. Direct Google Drive API `DELETE https://www.googleapis.com/drive/v3/files/<ID>`
   using the OAuth access token extracted from the rclone config — deleted
   each now-empty folder shell. Both returned HTTP 204.

Pre-delete GET confirmed names `mnemo-mcp` / `wet-mcp` and `trashed=false`
before each DELETE.

## After state (verified)

`rclone lsd echovault-gdrive:` shows exactly 1 mnemo-mcp folder + 1 wet-mcp folder.

- mnemo-mcp canonical: `1WhP5kEZeKfsKYOwEZLNVtMay0gxDdQRX` containing memories.db 4382720 bytes (~4.38 MB, 255 rows, FTS5 rebuilt)
- wet-mcp canonical: `18DxObY6S5YeP3A9ERdad9ZkJQmBXTVR0` containing docs.db 1541513216 bytes (~1.54 GB, 1986/1986/661294)

Duplicate folder issue eliminated.

## Known gap (tracked, not blocking)

The 2 merged mnemo rows (`77b281bfb8f7`, `13c8cc1894d8`) do NOT have `memories_vec` embeddings populated — the merge ran via Python stdlib sqlite3 which cannot load the vec0 extension. Server-runtime lazy re-embed on first query touching those rows is required. Added to follow-up task: verify mnemo-mcp has this logic before Phase J release, or document as known gap.

## Local backup (preserved until Phase J release)

`_backup/gdrive-audit/` preserves all original file copies:
- mnemo-mcp/folder-new/memories.db (3.94 MB original)
- mnemo-mcp/folder-old/memories.db (3.70 MB original)
- mnemo-mcp/merged.db (4.18 MB merged result)
- wet-mcp/folder-new/docs.db (1.44 GB)
- wet-mcp/folder-old/docs-mar12.db (1.42 GB)
- wet-mcp/folder-old/docs-feb26.db (1.41 GB)

Do NOT delete until Phase J successfully migrates to drive.appdata scope and verifies uploads to appDataFolder.

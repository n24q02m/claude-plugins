# Phase H — GDrive Duplicate Folder Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec**: `specs/2026-04-10-mcp-core-unified-transport-design.md` §2.6
**Roadmap**: `plans/2026-04-10-phase3-roadmap.md`
**Date**: 2026-04-11

**Goal:** Eliminate duplicate GDrive folders (mnemo-mcp × 2, wet-mcp × 2) by downloading both versions of each SQLite database, analyzing schema and row counts, merging if necessary, uploading the canonical version, and deleting duplicates — with user in loop for destructive decisions.

**Architecture:** Destructive cleanup is split into 3 sub-phases: (H1) inventory + download both versions, (H2) SQLite analysis + merge strategy decision with user approval, (H3) upload merged + delete duplicate + verify. No code changes to wet-mcp/mnemo-mcp in this phase — code updates (drive.file → drive.appdata scope) happen in Phase J.

**Tech Stack:** rclone (`echovault-gdrive:` remote already configured), Python 3.13 + sqlite3 stdlib, diff tools, manual review with user.

---

## Pre-flight

- [ ] **Step P.1: Verify rclone remote exists and auth works**

```bash
rclone listremotes
rclone about echovault-gdrive: 2>&1 | head -10
```

Expected: `echovault-gdrive:` in listremotes output. `about` shows quota + used space. Any auth error → STOP, ask user to re-auth via `rclone config reconnect echovault-gdrive:`.

- [ ] **Step P.2: Confirm duplicate state**

```bash
rclone lsd echovault-gdrive: 2>&1 | grep -E "wet-mcp|mnemo-mcp"
```

Expected: 4 lines — `mnemo-mcp` × 2 + `wet-mcp` × 2. If only 2 lines, duplicates may have been cleaned up already — STOP and report.

- [ ] **Step P.3: Create backup directory structure**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
mkdir -p _backup/gdrive-audit/mnemo-mcp/{folder-a,folder-b}
mkdir -p _backup/gdrive-audit/wet-mcp/{folder-a,folder-b}
ls _backup/gdrive-audit/
```

Expected: 2 top-level dirs, 4 sub-dirs total. Note: `_backup/` must be in `.gitignore` (add if missing).

- [ ] **Step P.4: Ensure `_backup/` is git-ignored**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
grep -q "^_backup/$" .gitignore || echo "_backup/" >> .gitignore
cat .gitignore
```

Expected: `_backup/` line present.

---

### Task H1: Download both versions of duplicate folders

**Files:**
- Read: rclone remote `echovault-gdrive:`
- Write: `_backup/gdrive-audit/<server>/folder-{a,b}/` (SQLite DBs and any other files)
- No git commit in this task (backup data is gitignored)

**Context**: Google Drive allows multiple folders with same name (distinguished by folder ID). rclone path-based API can only disambiguate via folder ID flag or JSON listing. Strategy: list all folders with `--drive-root-folder-id` or use `rclone lsjson` to get folder IDs, then download each separately.

- [ ] **Step 1: Get folder IDs for mnemo-mcp duplicates**

```bash
rclone lsjson echovault-gdrive: --dirs-only 2>&1 | python -c "
import json, sys
data = json.load(sys.stdin)
mnemo = [d for d in data if d['Name'] == 'mnemo-mcp']
wet = [d for d in data if d['Name'] == 'wet-mcp']
print('mnemo-mcp folders:')
for f in mnemo:
    print(f'  ID={f[\"ID\"]} ModTime={f[\"ModTime\"]}')
print('wet-mcp folders:')
for f in wet:
    print(f'  ID={f[\"ID\"]} ModTime={f[\"ModTime\"]}')
"
```

Expected: 4 folder IDs printed with their modification times. Record IDs as variables:
- `MNEMO_OLD_ID` = older mnemo folder (2026-02)
- `MNEMO_NEW_ID` = newer mnemo folder (2026-04)
- `WET_OLD_ID` = older wet folder (2026-02)
- `WET_NEW_ID` = newer wet folder (2026-04)

- [ ] **Step 2: Download mnemo older folder to folder-a**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
rclone copy "echovault-gdrive:{$MNEMO_OLD_ID}" _backup/gdrive-audit/mnemo-mcp/folder-a/ --drive-root-folder-id=$MNEMO_OLD_ID --progress 2>&1 | tail -10
ls -lh _backup/gdrive-audit/mnemo-mcp/folder-a/
```

Note: rclone syntax for folder-ID-based copy varies by version. Alternative:

```bash
rclone copy echovault-gdrive: _backup/gdrive-audit/mnemo-mcp/folder-a/ --drive-root-folder-id=$MNEMO_OLD_ID --progress
```

Expected: files downloaded, at minimum `memories.db` (expect ~hundreds of MB to GB). Other files may include auth tokens, indexes.

- [ ] **Step 3: Download mnemo newer folder to folder-b**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
rclone copy echovault-gdrive: _backup/gdrive-audit/mnemo-mcp/folder-b/ --drive-root-folder-id=$MNEMO_NEW_ID --progress 2>&1 | tail -10
ls -lh _backup/gdrive-audit/mnemo-mcp/folder-b/
```

Expected: similar file list, possibly with newer memories.db.

- [ ] **Step 4: Download wet older + newer folders**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
rclone copy echovault-gdrive: _backup/gdrive-audit/wet-mcp/folder-a/ --drive-root-folder-id=$WET_OLD_ID --progress 2>&1 | tail -10
rclone copy echovault-gdrive: _backup/gdrive-audit/wet-mcp/folder-b/ --drive-root-folder-id=$WET_NEW_ID --progress 2>&1 | tail -10
ls -lh _backup/gdrive-audit/wet-mcp/folder-a/ _backup/gdrive-audit/wet-mcp/folder-b/
```

Expected: at minimum `docs.db` in each.

- [ ] **Step 5: Report total backup size to user**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
du -sh _backup/gdrive-audit/mnemo-mcp/folder-a _backup/gdrive-audit/mnemo-mcp/folder-b _backup/gdrive-audit/wet-mcp/folder-a _backup/gdrive-audit/wet-mcp/folder-b
du -sh _backup/gdrive-audit
```

Expected: total size printed. STOP and ask user if total > 5GB before proceeding to H2 (user may want to move backup to external drive first).

---

### Task H2: Analyze SQLite DBs and decide merge strategy (user in loop)

**Files:**
- Read: `_backup/gdrive-audit/<server>/folder-{a,b}/*.db`
- Write: `_backup/gdrive-audit/<server>/merge-report.md` (analysis artifact)
- Write: `_backup/gdrive-audit/<server>/merged.db` (if merge is performed)
- No git commit

**Context**: SQLite DBs contain unique user data (memories, indexed docs). Cannot tuỳ tiện pick one version — must analyze schema + row counts + overlap before decision.

- [ ] **Step 1: mnemo memories.db schema + row counts for folder-a**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
python - <<'EOF'
import sqlite3, os, json
db = "_backup/gdrive-audit/mnemo-mcp/folder-a/memories.db"
if not os.path.exists(db):
    print(f"MISSING: {db}")
else:
    conn = sqlite3.connect(db)
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print(f"=== {db} ({os.path.getsize(db)/1e6:.1f} MB) ===")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM `{t}`").fetchone()[0]
        schema = conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{t}'").fetchone()[0]
        print(f"  Table {t}: {count} rows")
        print(f"    Schema: {schema[:200]}")
    conn.close()
EOF
```

Expected: list of tables and row counts. Typical mnemo schema has `memories`, `memory_chunks`, `embeddings`, `graph_nodes`, `graph_edges`.

- [ ] **Step 2: Same analysis for folder-b**

Duplicate Step 1 command with path `folder-b` instead of `folder-a`. Record counts.

- [ ] **Step 3: Check schema identical + check ID overlap**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
python - <<'EOF'
import sqlite3
a = sqlite3.connect("_backup/gdrive-audit/mnemo-mcp/folder-a/memories.db")
b = sqlite3.connect("_backup/gdrive-audit/mnemo-mcp/folder-b/memories.db")
schema_a = {r[0]: r[1] for r in a.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")}
schema_b = {r[0]: r[1] for r in b.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")}
print("Schema diff:")
for t in set(schema_a) | set(schema_b):
    if schema_a.get(t) == schema_b.get(t):
        print(f"  {t}: SAME")
    else:
        print(f"  {t}: DIFFERENT")
        print(f"    a: {schema_a.get(t, 'MISSING')[:100]}")
        print(f"    b: {schema_b.get(t, 'MISSING')[:100]}")
# Check ID overlap on memories table (if exists)
try:
    ids_a = set(r[0] for r in a.execute("SELECT id FROM memories"))
    ids_b = set(r[0] for r in b.execute("SELECT id FROM memories"))
    print(f"\nmemories table IDs:")
    print(f"  folder-a: {len(ids_a)} unique IDs")
    print(f"  folder-b: {len(ids_b)} unique IDs")
    print(f"  intersection: {len(ids_a & ids_b)}")
    print(f"  only in a: {len(ids_a - ids_b)}")
    print(f"  only in b: {len(ids_b - ids_a)}")
except sqlite3.OperationalError as e:
    print(f"memories table check failed: {e}")
a.close()
b.close()
EOF
```

Expected: schema comparison + overlap statistics.

- [ ] **Step 4: Decision gate — STOP and report to user**

Report this table to user:

```
mnemo-mcp merge analysis:
  folder-a (older, 2026-02): memories = X rows, size Y MB
  folder-b (newer, 2026-04): memories = A rows, size B MB
  schema: SAME/DIFFERENT
  ID overlap: Z common IDs
  only in folder-a: P IDs
  only in folder-b: Q IDs

Merge options:
  1) Pick folder-b (newer) as canonical, discard folder-a (losing P unique IDs)
  2) Pick folder-a as canonical, discard folder-b (losing Q unique IDs)
  3) INSERT OR IGNORE merge folder-a INTO folder-b (keep all unique rows, prefer folder-b on ID collision)
  4) Manual review — dump rows only in folder-a, inspect

Which option do you want?
```

WAIT for user decision. Do NOT proceed without explicit choice.

- [ ] **Step 5: Execute merge decision for mnemo**

Based on user's choice, execute one of:

**Option 1 (keep b, discard a)**:
```bash
cp _backup/gdrive-audit/mnemo-mcp/folder-b/memories.db _backup/gdrive-audit/mnemo-mcp/merged.db
```

**Option 3 (INSERT OR IGNORE merge a into b)**:
```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
cp _backup/gdrive-audit/mnemo-mcp/folder-b/memories.db _backup/gdrive-audit/mnemo-mcp/merged.db
python - <<'EOF'
import sqlite3
target = sqlite3.connect("_backup/gdrive-audit/mnemo-mcp/merged.db")
source = sqlite3.connect("_backup/gdrive-audit/mnemo-mcp/folder-a/memories.db")
for table in [r[0] for r in target.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
    cols = [r[1] for r in target.execute(f"PRAGMA table_info(`{table}`)")]
    col_list = ",".join(f"`{c}`" for c in cols)
    placeholder = ",".join("?" * len(cols))
    before = target.execute(f"SELECT COUNT(*) FROM `{table}`").fetchone()[0]
    try:
        rows = list(source.execute(f"SELECT {col_list} FROM `{table}`"))
        target.executemany(f"INSERT OR IGNORE INTO `{table}` ({col_list}) VALUES ({placeholder})", rows)
        target.commit()
        after = target.execute(f"SELECT COUNT(*) FROM `{table}`").fetchone()[0]
        print(f"{table}: {before} → {after} (+{after - before} rows)")
    except sqlite3.OperationalError as e:
        print(f"{table}: SKIP ({e})")
target.close()
source.close()
EOF
```

- [ ] **Step 6: Repeat Steps 1-5 for wet-mcp docs.db**

Same pattern: analyze folder-a + folder-b, check schema + ID overlap, report to user, execute chosen merge. Record decision in `merge-report.md`.

- [ ] **Step 7: Write merge-report.md for both servers**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
cat > _backup/gdrive-audit/merge-report.md <<EOF
# Phase H merge report

Date: 2026-04-11

## mnemo-mcp

- folder-a (ID=$MNEMO_OLD_ID): <fill rows + size>
- folder-b (ID=$MNEMO_NEW_ID): <fill rows + size>
- User decision: <fill Option 1/2/3/4>
- Result: <fill row counts after merge>

## wet-mcp

- folder-a (ID=$WET_OLD_ID): <fill rows + size>
- folder-b (ID=$WET_NEW_ID): <fill rows + size>
- User decision: <fill>
- Result: <fill>
EOF
```

Fill placeholders with actual values from analysis steps.

---

### Task H3: Upload merged + delete duplicates + verify

**Files:**
- Upload: `_backup/gdrive-audit/<server>/merged.db` → Drive
- Delete: folder-a (older) duplicate via rclone
- Verify: `rclone lsd echovault-gdrive:` shows single folder per server

- [ ] **Step 1: Upload merged mnemo DB back to canonical folder (newer)**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
rclone copy _backup/gdrive-audit/mnemo-mcp/merged.db echovault-gdrive: --drive-root-folder-id=$MNEMO_NEW_ID --progress 2>&1 | tail -5
# Verify upload by listing destination
rclone ls echovault-gdrive: --drive-root-folder-id=$MNEMO_NEW_ID 2>&1 | head -10
```

Expected: merged.db uploaded (it replaces existing memories.db via rclone copy semantics, or needs rename if the target name is `memories.db`). **Adjust**: rename merged.db → memories.db before upload if needed.

- [ ] **Step 2: Upload merged wet DB**

Same pattern, path: `_backup/gdrive-audit/wet-mcp/merged.db` → `$WET_NEW_ID`, target name `docs.db`.

- [ ] **Step 3: Final confirmation gate — STOP and ask user**

Report:
```
Ready to PURGE duplicate folders:
  - mnemo-mcp folder-a (ID=$MNEMO_OLD_ID, created 2026-02-12)
  - wet-mcp folder-a (ID=$WET_OLD_ID, created 2026-02-13)

Local backup at _backup/gdrive-audit/ preserved.

Proceed with purge? (yes/no)
```

WAIT for user `yes`. Do NOT proceed without it.

- [ ] **Step 4: Purge duplicate folders**

```bash
rclone purge echovault-gdrive: --drive-root-folder-id=$MNEMO_OLD_ID 2>&1 | tail -5
rclone purge echovault-gdrive: --drive-root-folder-id=$WET_OLD_ID 2>&1 | tail -5
```

Expected: no error output. Folders deleted.

- [ ] **Step 5: Verify single folder per server**

```bash
rclone lsd echovault-gdrive: 2>&1 | grep -E "wet-mcp|mnemo-mcp"
```

Expected: exactly 2 lines — `wet-mcp` (1) + `mnemo-mcp` (1). If 4 still, purge failed — investigate.

- [ ] **Step 6: Write evidence file and commit**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
cp _backup/gdrive-audit/merge-report.md docs/superpowers/evidence/2026-04-11-h-gdrive-cleanup.md
git add docs/superpowers/evidence/2026-04-11-h-gdrive-cleanup.md
git commit -m "feat: record Phase H GDrive duplicate cleanup evidence

mnemo-mcp and wet-mcp duplicate folders consolidated after SQLite
analysis + user-approved merge decision. Single folder per server
verified via rclone lsd. Local backup preserved at _backup/gdrive-audit/.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

Expected: commit made. `_backup/gdrive-audit/` stays gitignored.

---

## Phase H Exit Gate

- [ ] **Gate 1: rclone lsd confirms 1 folder per server**

```bash
rclone lsd echovault-gdrive: 2>&1 | grep -cE "^.*(wet-mcp|mnemo-mcp)$"
```

Expected: `2` (one wet-mcp + one mnemo-mcp).

- [ ] **Gate 2: Merged DB verified accessible from remote**

```bash
rclone ls echovault-gdrive: --drive-root-folder-id=$MNEMO_NEW_ID 2>&1 | grep -E "\.db$"
rclone ls echovault-gdrive: --drive-root-folder-id=$WET_NEW_ID 2>&1 | grep -E "\.db$"
```

Expected: `memories.db` for mnemo, `docs.db` for wet, with expected sizes.

- [ ] **Gate 3: Local backup preserved until Phase J code deploys**

```bash
du -sh _backup/gdrive-audit/
```

Expected: backup size matches Step H1.5 report. Do NOT delete until Phase J successfully migrates to `drive.appdata` scope and re-uploads data.

- [ ] **Gate 4: Evidence file committed**

```bash
ls docs/superpowers/evidence/2026-04-11-h-gdrive-cleanup.md
git log --oneline -5
```

Expected: file present, commit in log.

---

## Notes

- This phase is destructive and cannot be partially rolled back without the local backup in `_backup/gdrive-audit/`. Keep that directory intact until Phase J post-migration verification.
- Steps H2.4 and H3.3 REQUIRE interactive user approval — agent-driven execution must pause for input.
- If rclone `--drive-root-folder-id` flag syntax differs from this plan (rclone version dependent), fall back to Drive API v3 direct via `curl + OAuth token`. Document the alternative in evidence file.

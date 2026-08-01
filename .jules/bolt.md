Dates below are the dates the change landed on `main`, taken from `git log`.
Each entry carries the commit holding it, so an entry can be located in the
repository history before the same change is proposed again.

## 2026-07-18 - Everything under `plugins/` is generated; a patch there is erased at the next sync
**Commit:** 8999881
**Learning:** `plugins/<repo>/` is a mirror of a source repository, not source in its own right. `.github/workflows/cd.yml` runs on `repository_dispatch: plugin-sync` whenever one of the nine source repos publishes a release, and `scripts/sync-plugins.sh` rebuilds the tree with `rm -rf "$dst/$dir_name"` followed by `cp -r`. A patch applied to a mirrored file therefore survives only until that plugin's next release. This is not hypothetical: 7fce140 (2026-07-17) added ten lines of argument validation to `plugins/wet-mcp/skills/research-topic/scripts/run.py`, and 8999881 (2026-07-18) synced wet-mcp 3.6.0 and deleted all ten the following day. `CLAUDE.md` already carries the rule -- "Sync script pulls latest from source repos -- do not edit plugin files directly" -- and every proposal listed under Rejected below ignored it.
**Action:** Before proposing a change, check whether the file sits under `plugins/`. If it does, the change belongs in the source repository (`n24q02m/wet-mcp`, `n24q02m/agent-chat-plugin`, and so on), where it will be reviewed once and then reach this repository through the sync. The paths that are genuinely reviewable here are `scripts/`, `.github/`, `docs/`, and `.claude-plugin/marketplace.json`.

## 2026-07-18 - Hoisted the regexes in the agent-chat message scan
**Commit:** b16b816
**Learning:** `message_files` compiled `^(\d+)-` once per file through `re.match` with a literal pattern, and `slugify` recompiled `[^a-z0-9]+` on every call. Both run once per message per scan, and the scan runs on every `read`, `wait` poll and SessionStart hook, so the compile cache lookup was being paid in the one loop that repeats. Hoisting them to module level (`_SEQ_RE`, `_NON_ALNUM_RE`) also let the sort read `_seq_from_name` once per file instead of once per comparison.
**Action:** Hoist a pattern to module scope when the call site is inside a per-message loop. Note the caveat above: this commit edited a mirrored file, so it will not survive the next `agent-chat-plugin` sync unless the same change also exists upstream. That is an argument for making the change upstream first, not for repeating it here.

## 2026-07-25 - The frontmatter streaming read is already in the source repository
**Commit:** `agent-chat-plugin@ce79b70c` (source repository; not in this repository's history)
**Learning:** Replacing `path.read_text()` in `parse_frontmatter` with a line-by-line reader that stops at the closing `---` is a real improvement, and it was reviewed, measured and merged upstream on 2026-07-25 as "fix: parse frontmatter without reading the whole message". `n24q02m/agent-chat-plugin/.jules/bolt.md` carries the decision and asks that further proposals arrive with a measurement. Measured again here on this machine's real corpus (`$AGENT_CHAT_ROOT/*/*.md`, 82 messages, 165314 bytes, median message 1788 B, largest 7879 B), full sweep of all 82 files, minimum of 200 runs because eight other agents were contending for the disk and the median was unusable: 12.913 ms to 11.210 ms, a 1.703 ms saving, 13.2 percent, about 20.8 microseconds per file. Both implementations produced identical output on all 82 files. The saving is genuine but small at the sizes this repository actually sees; it only becomes decisive on bodies this corpus does not contain -- on a synthetic file with the same eight-line frontmatter the delta is -5.8 percent at a 2 KB body, -24.5 percent at 8 KB, -58.4 percent at 64 KB and -97.8 percent at 1 MB, because the old code's cost scales with the body it never uses while the new code's does not.
**Action:** The change is settled and lives upstream; the copy under `plugins/agent-chat-plugin/` picks it up at the next sync. Do not re-propose it here. For any future proposal on this path, quote a before-and-after measurement taken on this repository's own corpus, and use the minimum of at least 20 runs rather than the mean when the machine is busy.

## Rejected

Proposals that were reviewed and turned down, with the reason. They are recorded
here so the reason travels with the repository instead of staying behind in a
closed pull request.

### 2026-07-18 to 2026-07-31 - Fourteen rewrites of `parse_frontmatter` in the mirrored copy (#546, #547, #552, #553, #556, #560, #563, #567, #570, #576, #578, #582, #585, #587)
**Proposed:** replace `path.read_text()` in `plugins/agent-chat-plugin/chat.py` with a reader that stops at the closing `---`. One proposal per day for two weeks, each opened against a fresh branch with no reference to the previous thirteen.
**Why rejected:** not on the merits of the optimisation, which is sound and is recorded as accepted above. Two reasons. First, the file is a mirror; merging any of these would have been undone by the next `agent-chat-plugin` release exactly as 8999881 undid 7fce140. Second, the change is already in the source repository as of 2026-07-25, so the mirror converges on its own. The fourteen diffs never converged on each other either -- they alternate between `open(path, "r", ...)` and `path.open(...)`, between `line.strip()` and `line.rstrip("\r\n")`, and between assigning into `meta` directly and staging through a temporary dict -- which is what proposals generated without reading the previous ones look like.
**Action:** Check `git log` for the file and this ledger before opening a performance proposal. If the file is under `plugins/`, open it against the source repository instead.

### 2026-07-18 - Comments in source naming the tool and asserting an unmeasured speedup (#546 and others in the cluster)
**Proposed:** annotate the rewritten block with a comment naming the optimisation and the improvement it was expected to deliver.
**Why rejected:** this repository is public, and the comment asserted a benefit no measurement in the pull request supported. A note of that shape is noise for every later reader of the file, and it dates badly once the surrounding code moves.
**Action:** Write comments that explain why the code is shaped the way it is, in the voice of the surrounding file. Leave authorship to the commit metadata and the speedup to the commit message, where it can be checked against a number.

### 2026-07-28 to 2026-07-31 - Unrelated reformatting carried alongside the optimisation (#578, #585, #587)
**Proposed:** in the same diff as the frontmatter change, a blank line added after the module docstring of `plugins/agent-chat-plugin/hooks/session_inbox.py`, and in #587 a re-wrap of two decorators in `plugins/better-workspace-mcp/hooks/tests/test_check_credentials.py`.
**Why rejected:** neither file has anything to do with frontmatter parsing, and the second belongs to a different plugin entirely. Formatting churn in a mirrored tree is churn twice over: it cannot outlive the next sync, and it widens the diff a reviewer has to read to find the change the title describes.
**Action:** Keep the diff to the files the title names. Formatting of mirrored files is settled by the source repository's own formatter.

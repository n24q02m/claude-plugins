Dates below are the dates the change landed on `main`, taken from `git log`.
Each entry carries the commit holding it, so an entry can be located in the
repository history before the same change is proposed again.

## 2026-08-01 - What the Palette remit covers in this repository
**Commit:** (scope note; records no code change)
**Learning:** This repository is a marketplace and a documentation site, not an application, so "user interface" here means prose and metadata rather than components. The surfaces a reader actually meets are the Astro Starlight site under `docs/src/content/docs/` (`index.mdx`, `get-started/`, `reference/`), the per-plugin setup prose under `plugins/*/`, `README.md`, the descriptions and titles in `.claude-plugin/marketplace.json` that render in the plugin picker, and the messages the scripts in `scripts/` print when they fail. Those last two are easy to overlook and are the ones a user reads at the moment something has gone wrong.
**Action:** Direct Palette work at those paths. Note the boundary: `scripts/sync-plugins.sh` regenerates `plugins/<repo>/.claude-plugin/plugin.json`, `gemini-extension.json`, `skills/`, `hooks/`, `commands/` and `chat.py` from the source repositories, so wording inside those is fixed upstream and a change to it here is erased at that plugin's next release. The setup prose alongside them in `plugins/*/` is not regenerated and is edited here.

## 2026-08-01 - A conclusion that nothing needs changing is an entry, not a pull request
**Commit:** (scope note; records no code change)
**Learning:** #548 examined the Starlight docs, concluded there was no UX change worth making, and delivered that conclusion as a pull request changing no files, which then sat open for thirteen days. The conclusion may well have been right. The delivery was not: an empty pull request consumes a review cycle, runs the full check matrix, and leaves a branch to prune, all to communicate one sentence. `n24q02m/mnemo-mcp` reached the same conclusion three times the same way (#1003, #1007, #1032) before recording it in its own ledger.
**Action:** When a pass over the documentation finds nothing worth changing, write that here as a dated entry naming the surfaces examined, and open no pull request. A later pass can then start from what was already looked at instead of repeating it.

## Rejected

Proposals that were reviewed and turned down, with the reason. They are recorded
here so the reason travels with the repository instead of staying behind in a
closed pull request.

### 2026-07-18 - Empty pull request to create this journal (#544)
**Proposed:** initialise the Palette journal, delivered as a pull request changing no files (`+0/-0`).
**Why rejected:** rejected only in its delivered form. The request was right and this file is the answer to it, but the pull request contained no file. The reason is worth recording because it will catch the next attempt too: `.gitignore` ignores `.jules/` (three times over, at lines 6, 7 and 18, the last as `.Jules/`), so a newly created ledger is silently skipped by `git add` and the commit comes out empty. `.jules/sentinel.md` predates or bypassed that rule and is tracked, which is why editing it works while creating a sibling does not. wet-mcp and mnemo-mcp ignore `.jules/` as well and carry all three ledgers regardless, so the stack convention is to force the file into the index once; after that it is tracked and ordinary edits apply. This file and `bolt.md` were added with `git add -f`.
**Action:** To start a ledger here, `git add -f .jules/<name>.md` with its first entry already written. If a commit meant to add a file reports nothing to commit, check `git check-ignore -v` on the path before concluding there was nothing to say.

### 2026-07-19 - Empty pull request announcing that no change was needed (#548)
**Proposed:** report, as a pull request changing no files, that no UX enhancements were identified in the Starlight docs.
**Why rejected:** same shape as #544 and as mnemo #1003, #1007 and #1032. The finding belongs in this file, where the next pass will see it; in a closed pull request it is invisible to everything that reads the repository.
**Action:** Record the skip as the entry above does, naming the surfaces examined and the date, so the next pass can begin where this one stopped.

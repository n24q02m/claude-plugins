# Phase G3 — CodeQL false-positive dismissals

Date: 2026-04-11
Executed by: Claude Code session (Phase G3 subagent)
Spec: `specs/2026-04-10-mcp-core-unified-transport-design.md`
Plan: `plans/2026-04-11-phase-g-unblock.md`

## Dismissed (15 total)

- **wet-mcp**: #98, 67, 66, 65, 64, 63, 62, 61, 60, 59
- **mnemo-mcp**: #1, 2, 3
- **web-core**: #1, 2

All 15 match rule `py/incomplete-url-substring-sanitization` in test files.

## Justification

Test assertions use `substring in url` to verify that URL responses contain
expected domain names. These are unit test assertions, NOT runtime sanitization.
CodeQL rule targets production code security boundaries where untrusted input
is substring-matched. No untrusted input reaches test code. False positive by
rule scope.

## Verification

```
gh api "repos/n24q02m/wet-mcp/code-scanning/alerts?state=open" --jq 'length' → 0
gh api "repos/n24q02m/mnemo-mcp/code-scanning/alerts?state=open" --jq 'length' → 0
gh api "repos/n24q02m/web-core/code-scanning/alerts?state=open" --jq 'length' → 0
```

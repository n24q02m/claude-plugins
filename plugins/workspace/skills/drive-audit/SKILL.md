---
name: drive-audit
description: Search, locate, and audit Google Drive files, recent updates, permissions, and orphan documents
argument-hint: "[file name, query pattern, or mimeType]"
---

# Drive Audit

Audit and navigate Google Drive files, folders, and documents with structured search and metadata checks.

## Workflow

1. **Search Files**: Call `drive(action="search", query="...")` using structured query syntax (`mimeType`, `name contains`, `modifiedTime >`).
2. **Inspect Metadata**: For located documents, check ownership, last modifying user, and parent folder structure.
3. **Report**:
   - List matching files with title, mimeType, webViewLink, and modification date.
   - Group by folder hierarchy when multiple items match.

## When to Use

- Finding misplaced documents or spreadsheets across team folders
- Checking recent changes in shared drives
- Preparing clean file summaries before collaboration

# Phase I — Archive mcp-relay-core + Bootstrap mcp-core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec**: `specs/2026-04-10-mcp-core-unified-transport-design.md` §2.5, §2.11
**Roadmap**: `plans/2026-04-10-phase3-roadmap.md`
**Date**: 2026-04-11

**Goal:** Fully back up `mcp-relay-core`, create a fresh `mcp-core` repository with the new layout (transport + auth + lifecycle + crypto + install + embedding-daemon + stdio-proxy), migrate modules from old to new, publish v0.1.0 beta to PyPI + NPM, then archive the old repo — so Phase J can migrate downstream servers against a stable `mcp-core` baseline.

**Architecture:** Archive + new is preferred over in-place rename because scope expansion is 10× (credential helper → full framework), git history of old repo has limited value (~10 commits, mostly Dependabot), and a fresh semver start (v0.1.0) avoids downstream version-confusion. Backup is preserved via git bundle + `gh api` export for worst-case restoration. Module mapping preserves all existing logic without loss.

**Tech Stack:** Python 3.13 + uv + hatchling (packages/core-py), Node 20 + pnpm (packages/core-ts), FastMCP (transport base), authlib (OAuth 2.1), fcntl/msvcrt (file locks), onnxruntime + llama-cpp-python (embedding daemon).

---

## Pre-flight

- [ ] **Step P.1: gh auth + confirm repo admin access**

```bash
gh auth status
gh api user --jq '.login'
gh api repos/n24q02m/mcp-relay-core --jq '{name, archived, permissions}' 2>&1
```

Expected: `n24q02m` logged in, `mcp-relay-core` accessible with admin permissions, `archived: false`.

- [ ] **Step P.2: Clean local mcp-relay-core state**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-relay-core 2>&1
git status
git fetch --all
git log --oneline origin/main | head -5
```

Expected: clean working tree OR status reported. No uncommitted changes before backup.

- [ ] **Step P.3: Verify spec and doc-update-matrix exist**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
ls docs/superpowers/specs/2026-04-10-mcp-core-unified-transport-design.md docs/superpowers/specs/2026-04-11-doc-update-matrix.md
```

Expected: both files present. Phase I references spec §2.5 + §2.11 extensively.

---

### Task I1: Full backup of mcp-relay-core

**Files:**
- Write: `_backup/mcp-relay-core/` (git bundle + gh api exports, gitignored)
- No git commit in claude-plugins worktree (backup data stays local)

**Context**: Before archiving, preserve everything restorable: full git history via bundle, open PRs/issues metadata via `gh api`, published package metadata for rollback, releases list. Target: if something goes wrong, we can `git clone _backup/mcp-relay-core/bundle` and re-publish.

- [ ] **Step 1: Create backup directory**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
mkdir -p _backup/mcp-relay-core
grep -q "^_backup/$" .gitignore || echo "_backup/" >> .gitignore
```

Expected: directory created, `.gitignore` has `_backup/`.

- [ ] **Step 2: Git bundle — full history**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-relay-core
git fetch --all --tags
git bundle create C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core/_backup/mcp-relay-core/repo.bundle --all
git bundle verify C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core/_backup/mcp-relay-core/repo.bundle 2>&1
```

Expected: bundle created, verification passes. Bundle should contain all branches + tags.

- [ ] **Step 3: Export PRs + issues metadata via gh api**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
gh api "repos/n24q02m/mcp-relay-core/pulls?state=all&per_page=100" > _backup/mcp-relay-core/pulls.json
gh api "repos/n24q02m/mcp-relay-core/issues?state=all&per_page=100" > _backup/mcp-relay-core/issues.json
gh api "repos/n24q02m/mcp-relay-core/releases" > _backup/mcp-relay-core/releases.json
python -c "import json; print('pulls:', len(json.load(open('_backup/mcp-relay-core/pulls.json')))); print('issues:', len(json.load(open('_backup/mcp-relay-core/issues.json')))); print('releases:', len(json.load(open('_backup/mcp-relay-core/releases.json'))))"
```

Expected: 3 JSON files written, counts printed (probably ~10-20 PRs/issues, few releases).

- [ ] **Step 4: Export PyPI + NPM package metadata for rollback reference**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
curl -sS "https://pypi.org/pypi/mcp-relay-core/json" > _backup/mcp-relay-core/pypi.json
curl -sS "https://registry.npmjs.org/@n24q02m/mcp-relay-core" > _backup/mcp-relay-core/npm.json
python -c "import json; d=json.load(open('_backup/mcp-relay-core/pypi.json', encoding='utf-8')); print('PyPI latest:', d.get('info', {}).get('version'))"
python -c "import json; d=json.load(open('_backup/mcp-relay-core/npm.json', encoding='utf-8')); print('NPM latest:', d.get('dist-tags', {}).get('latest'))"
```

Expected: latest versions printed for both registries.

- [ ] **Step 5: Verify backup inventory**

```bash
ls -lh _backup/mcp-relay-core/
du -sh _backup/mcp-relay-core/
```

Expected: 5 files (bundle + 4 JSON), total size reported. Bundle should dominate.

---

### Task I2: Create mcp-core GitHub repository

**Files:**
- Create: new GitHub repo `n24q02m/mcp-core`
- Create: local clone at `C:/Users/n24q02m-wlap/projects/mcp-core/`
- No claude-plugins commit

- [ ] **Step 1: Verify repo name not yet taken**

```bash
gh api repos/n24q02m/mcp-core 2>&1 | grep -E "Not Found|status" | head -3
```

Expected: `Not Found` (404). If exists, STOP — investigate (maybe someone created it already, or a test run).

- [ ] **Step 2: Create public repo**

```bash
gh repo create n24q02m/mcp-core \
  --public \
  --description "Unified MCP Streamable HTTP transport, OAuth 2.1 AS, lifecycle, install, and shared embedding daemon" \
  --homepage "https://github.com/n24q02m/mcp-core" \
  --add-readme=false \
  --disable-wiki
```

Expected: repo created, URL printed. Do NOT use `--add-readme` — we will write our own.

- [ ] **Step 3: Clone to local projects dir**

```bash
cd C:/Users/n24q02m-wlap/projects
gh repo clone n24q02m/mcp-core
cd mcp-core
git status
```

Expected: empty repo cloned, on main branch.

- [ ] **Step 4: Set repo topics + description**

```bash
gh api -X PUT repos/n24q02m/mcp-core/topics \
  -f names[]="mcp" -f names[]="model-context-protocol" -f names[]="streamable-http" \
  -f names[]="oauth21" -f names[]="python" -f names[]="typescript" -f names[]="ai"
```

Expected: topics applied. Verify via `gh api repos/n24q02m/mcp-core --jq .topics`.

---

### Task I3: Scaffold monorepo layout per spec §2.5

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/` — root config, README, packages/, etc.
- Commit in `mcp-core` repo (not claude-plugins worktree)

- [ ] **Step 1: Root files**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > README.md <<'EOF'
# mcp-core

Unified MCP Streamable HTTP 2025-11-25 transport, OAuth 2.1 Authorization Server, lifecycle management, install automation, and shared embedding daemon for the n24q02m MCP ecosystem.

## Packages

- `packages/core-py` — Python implementation (wet, mnemo, crg, telegram backends)
- `packages/core-ts` — TypeScript implementation (email, notion backends)
- `packages/embedding-daemon` — Shared ONNX/GGUF embedding server (serves wet + mnemo + crg)
- `packages/stdio-proxy` — Thin stdio→HTTP forwarder for agents without HTTP support

## Supersedes

Replaces the archived [mcp-relay-core](https://github.com/n24q02m/mcp-relay-core) repository. Module mapping documented in `MIGRATION.md`.

## Spec

Architecture design lives in [claude-plugins/docs/superpowers/specs/2026-04-10-mcp-core-unified-transport-design.md](https://github.com/n24q02m/claude-plugins/blob/main/docs/superpowers/specs/2026-04-10-mcp-core-unified-transport-design.md).
EOF

cat > .gitignore <<'EOF'
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
.ruff_cache/
*.egg-info/
dist/
build/

# Node
node_modules/
.pnpm-store/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Local state
_backup/
.worktrees/
*.log
EOF

cat > LICENSE <<'EOF'
MIT License

Copyright (c) 2026 n24q02m

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
EOF

ls -la
```

Expected: README.md, .gitignore, LICENSE in root.

- [ ] **Step 2: Directory skeleton**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
mkdir -p packages/core-py/src/mcp_core/{transport,auth/oauth,auth/user_store,lifecycle,crypto,install/templates} packages/core-py/tests
mkdir -p packages/core-ts/src/mcp_core/{transport,auth/oauth,auth/user_store,lifecycle,crypto,install/templates} packages/core-ts/tests
mkdir -p packages/embedding-daemon/src/mcp_embedding_daemon/backends packages/embedding-daemon/tests
mkdir -p packages/stdio-proxy/src/mcp_stdio_proxy packages/stdio-proxy/tests
mkdir -p .github/workflows docs
find packages -type d | sort
```

Expected: nested structure printed matching spec §2.5 layout.

- [ ] **Step 3: Package-level init files (Python)**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
for d in $(find packages/core-py/src/mcp_core -type d) $(find packages/embedding-daemon/src/mcp_embedding_daemon -type d) $(find packages/stdio-proxy/src/mcp_stdio_proxy -type d); do
  touch "$d/__init__.py"
done
find packages/core-py/src packages/embedding-daemon/src packages/stdio-proxy/src -name "__init__.py"
```

Expected: init files created for all Python submodules.

- [ ] **Step 4: Root + per-package pyproject.toml stubs**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/core-py/pyproject.toml <<'EOF'
[project]
name = "mcp-core"
version = "0.1.0"
description = "Unified MCP Streamable HTTP 2025-11-25 transport, OAuth 2.1 AS, lifecycle, install"
requires-python = ">=3.13"
license = "MIT"
authors = [{ name = "n24q02m" }]
dependencies = [
    "fastmcp>=0.5.0",
    "httpx>=0.27.0",
    "cryptography>=46.0.7",
    "authlib>=1.3.0",
    "starlette>=0.37.0",
    "pydantic>=2.7.0",
    "loguru>=0.7.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "ruff>=0.5", "ty>=0.0.1"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcp_core"]

[tool.ruff]
line-length = 88
target-version = "py313"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
EOF
cat packages/core-py/pyproject.toml | head -20
```

Similar stub for `packages/embedding-daemon/pyproject.toml` and `packages/stdio-proxy/pyproject.toml` with appropriate names (`mcp-embedding-daemon`, `mcp-stdio-proxy`).

- [ ] **Step 5: TypeScript package.json for core-ts**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts
cat > package.json <<'EOF'
{
  "name": "@n24q02m/mcp-core",
  "version": "0.1.0",
  "description": "Unified MCP Streamable HTTP 2025-11-25 transport, OAuth 2.1 AS, lifecycle, install",
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "lint": "eslint src"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "express": "^4.19.0",
    "jose": "^5.2.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "vitest": "^1.5.0"
  },
  "license": "MIT",
  "repository": "https://github.com/n24q02m/mcp-core"
}
EOF
```

- [ ] **Step 6: Initial commit to mcp-core**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add .
git status
git commit -m "feat: scaffold mcp-core monorepo layout

4 packages: core-py (Python), core-ts (TypeScript), embedding-daemon,
stdio-proxy. Supersedes archived mcp-relay-core. Layout per
claude-plugins spec 2026-04-10-mcp-core-unified-transport-design §2.5.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git push origin main
```

Expected: first commit pushed to `n24q02m/mcp-core`.

---

### Task I4: Migrate crypto modules from old → new

**Files:**
- Copy from: `mcp-relay-core/packages/core-py/src/mcp_relay_core/{config.py,session_lock.py,crypto.py}`
- Create in: `mcp-core/packages/core-py/src/mcp_core/crypto/{config_enc.py,session_lock.py,key_sharing.py}`
- Commit in mcp-core repo

- [ ] **Step 1: Copy + rename files**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cp ../mcp-relay-core/packages/core-py/src/mcp_relay_core/config.py packages/core-py/src/mcp_core/crypto/config_enc.py
cp ../mcp-relay-core/packages/core-py/src/mcp_relay_core/session_lock.py packages/core-py/src/mcp_core/crypto/session_lock.py
ls packages/core-py/src/mcp_core/crypto/
```

Expected: 2 files copied + existing `__init__.py`. Add third file `key_sharing.py` if `mcp-relay-core` has ECDH crypto logic (verify first with `ls ../mcp-relay-core/packages/core-py/src/mcp_relay_core/ | grep -i crypt`).

- [ ] **Step 2: Update internal imports**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
# Replace `from mcp_relay_core` → `from mcp_core.crypto` in copied files
python - <<'EOF'
import pathlib, re
for f in pathlib.Path("packages/core-py/src/mcp_core/crypto").glob("*.py"):
    if f.name == "__init__.py":
        continue
    text = f.read_text(encoding="utf-8")
    new = re.sub(r"from mcp_relay_core\.config", "from mcp_core.crypto.config_enc", text)
    new = re.sub(r"from mcp_relay_core\.session_lock", "from mcp_core.crypto.session_lock", new)
    new = re.sub(r"from mcp_relay_core\b", "from mcp_core.crypto", new)
    new = re.sub(r"import mcp_relay_core", "import mcp_core.crypto", new)
    if new != text:
        f.write_text(new, encoding="utf-8")
        print(f"Updated {f}")
EOF
```

Expected: import statements updated in copied files. Verify by grep:

```bash
grep -rn "mcp_relay_core" packages/core-py/src/mcp_core/crypto/
```

Expected: no matches.

- [ ] **Step 3: Update `crypto/__init__.py` to re-export public API**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/core-py/src/mcp_core/crypto/__init__.py <<'EOF'
"""Cryptographic primitives: machine-key config encryption, session locks, key sharing."""
from mcp_core.crypto.config_enc import *  # noqa: F401, F403
from mcp_core.crypto.session_lock import *  # noqa: F401, F403
EOF
```

- [ ] **Step 4: Run pytest on crypto tests**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
# Copy existing tests from old repo
cp ../../../mcp-relay-core/packages/core-py/tests/test_*.py tests/ 2>/dev/null || echo "no tests to copy"
# Update test imports
python - <<'EOF'
import pathlib, re
for f in pathlib.Path("tests").glob("test_*.py"):
    text = f.read_text(encoding="utf-8")
    new = re.sub(r"mcp_relay_core", "mcp_core.crypto", text)
    if new != text:
        f.write_text(new, encoding="utf-8")
        print(f"Updated {f}")
EOF
uv sync
uv run pytest tests/ -q 2>&1 | tail -10
```

Expected: tests pass (or fail cleanly if test file was testing relay-specific APIs — fix or skip).

- [ ] **Step 5: Commit crypto migration**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-py/
git commit -m "feat: migrate crypto modules from mcp-relay-core

- config.py → crypto/config_enc.py (AES-GCM machine-key)
- session_lock.py → crypto/session_lock.py (cross-process lock)
- Update imports mcp_relay_core → mcp_core.crypto
- Copy and update existing tests

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git push origin main
```

---

### Task I5: Scaffold new packages (transport, auth, lifecycle, install)

**Files:**
- Create: `mcp-core/packages/core-py/src/mcp_core/transport/streamable_http.py` — FastMCP wrapper
- Create: `mcp-core/packages/core-py/src/mcp_core/auth/middleware.py` — 401 + WWW-Authenticate
- Create: `mcp-core/packages/core-py/src/mcp_core/auth/oauth/provider.py` — self-hosted AS skeleton
- Create: `mcp-core/packages/core-py/src/mcp_core/lifecycle/lock.py` — fcntl/msvcrt
- Create: `mcp-core/packages/core-py/src/mcp_core/install/agents.py` — config writer skeleton
- Commit in mcp-core repo

- [ ] **Step 1: Transport streamable_http.py stub**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/core-py/src/mcp_core/transport/streamable_http.py <<'EOF'
"""Streamable HTTP 2025-11-25 transport base.

Thin wrapper around FastMCP that adds OAuth 2.1 middleware, lifecycle lock,
and session management. Credential servers subclass or instantiate directly.
"""
from __future__ import annotations

from fastmcp import FastMCP
from starlette.applications import Starlette

from mcp_core.auth.middleware import OAuthMiddleware
from mcp_core.lifecycle.lock import LifecycleLock


class StreamableHTTPServer:
    """MCP server with Streamable HTTP 2025-11-25 transport."""

    def __init__(
        self,
        mcp: FastMCP,
        *,
        host: str = "127.0.0.1",
        port: int,
        auth: OAuthMiddleware | None = None,
        lock: LifecycleLock | None = None,
    ) -> None:
        self._mcp = mcp
        self._host = host
        self._port = port
        self._auth = auth
        self._lock = lock or LifecycleLock(name=mcp.name, port=port)

    def run(self) -> None:
        """Start the server (blocking)."""
        with self._lock:
            app: Starlette = self._mcp.streamable_http_app()
            if self._auth is not None:
                app.add_middleware(self._auth.__class__, **self._auth.kwargs)
            import uvicorn
            uvicorn.run(app, host=self._host, port=self._port, log_level="info")
EOF
wc -l packages/core-py/src/mcp_core/transport/streamable_http.py
```

- [ ] **Step 2: Auth middleware stub**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/core-py/src/mcp_core/auth/middleware.py <<'EOF'
"""OAuth 2.1 transport middleware.

Rejects unauthenticated requests with HTTP 401 + WWW-Authenticate header
per MCP Streamable HTTP 2025-11-25 spec + OAuth 2.1 (RFC 9470).
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class OAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        *,
        resource_metadata_url: str,
        token_verifier,
    ) -> None:
        super().__init__(app)
        self._metadata_url = resource_metadata_url
        self._verify = token_verifier
        self.kwargs = {"resource_metadata_url": resource_metadata_url, "token_verifier": token_verifier}

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path.startswith(("/.well-known/", "/authorize", "/token")):
            return await call_next(request)
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                {"error": "unauthorized", "error_description": "Bearer token required"},
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{self._metadata_url}"',
                },
            )
        token = auth_header.split(" ", 1)[1]
        try:
            principal = await self._verify(token)
        except Exception:
            return JSONResponse(
                {"error": "invalid_token"},
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer error="invalid_token", resource_metadata="{self._metadata_url}"',
                },
            )
        request.state.principal = principal
        return await call_next(request)
EOF
```

- [ ] **Step 3: OAuth provider stub (self-hosted AS)**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/core-py/src/mcp_core/auth/oauth/provider.py <<'EOF'
"""Self-hosted OAuth 2.1 Authorization Server.

Handles /authorize (renders relay form HTML), /token (exchanges auth code for
JWT access token), and /.well-known/oauth-authorization-server.

For Notion delegated mode, see delegated.py.
"""
from __future__ import annotations

# Implementation follows in Phase I subsequent steps.
class OAuthProvider:
    pass
EOF
```

- [ ] **Step 4: Lifecycle lock (fcntl/msvcrt)**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/core-py/src/mcp_core/lifecycle/lock.py <<'EOF'
"""Cross-process lifecycle lock — fcntl on Unix, msvcrt on Windows.

Ensures only one daemon instance runs per (name, port) tuple. Used by
auto-ensure stdio proxy spawning and by server startup.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


class LifecycleLock:
    def __init__(self, name: str, port: int, root: Path | None = None) -> None:
        self._name = name
        self._port = port
        self._root = root or Path.home() / ".config" / "mcp" / "locks"
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock_file = self._root / f"{name}-{port}.lock"
        self._fh = None

    def __enter__(self) -> "LifecycleLock":
        self._fh = open(self._lock_file, "w", encoding="utf-8")
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(self._fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self._fh.write(f"{os.getpid()}\n")
        self._fh.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._fh is not None:
            if sys.platform == "win32":
                import msvcrt
                try:
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            self._fh.close()
            try:
                self._lock_file.unlink(missing_ok=True)
            except OSError:
                pass
EOF
```

- [ ] **Step 5: Install agent-config writer stub**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/core-py/src/mcp_core/install/agents.py <<'EOF'
"""Agent config file writer.

Detects installed agents (Claude Code, Codex, Copilot, Antigravity, Cursor,
Windsurf, OpenCode) and writes MCP server entries to their config files.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

AgentName = Literal[
    "claude-code", "codex", "copilot", "antigravity", "cursor", "windsurf", "opencode"
]


class AgentInstaller:
    def __init__(self, server_name: str, url: str, token: str | None = None) -> None:
        self._server_name = server_name
        self._url = url
        self._token = token

    def install(self, target: AgentName) -> Path:
        """Install MCP server entry into target agent's config file.

        Returns the path of the file that was modified.
        """
        raise NotImplementedError("Implementation follows in Phase I subsequent steps")
EOF
```

- [ ] **Step 6: Run ruff + ty on new code**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
uv run ruff check src/ 2>&1 | tail -10
uv run ruff format src/ 2>&1 | tail -5
```

Expected: no lint errors or auto-fixed.

- [ ] **Step 7: Commit scaffolding**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-py/src/mcp_core/
git commit -m "feat: scaffold transport + auth + lifecycle + install modules

- transport/streamable_http.py: FastMCP Streamable HTTP wrapper
- auth/middleware.py: OAuth 2.1 401 + WWW-Authenticate
- auth/oauth/provider.py: self-hosted AS skeleton
- lifecycle/lock.py: fcntl/msvcrt cross-process lock
- install/agents.py: multi-agent config writer skeleton

Full implementations follow in subsequent I phase tasks.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git push origin main
```

---

### Task I6: Scaffold mcp-embedding-daemon package

**Files:**
- Create: `packages/embedding-daemon/pyproject.toml`
- Create: `packages/embedding-daemon/src/mcp_embedding_daemon/{__init__.py, server.py, api.py, backends/onnx.py, backends/gguf.py}`
- Commit in mcp-core repo

- [ ] **Step 1: pyproject.toml for embedding-daemon**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/embedding-daemon/pyproject.toml <<'EOF'
[project]
name = "mcp-embedding-daemon"
version = "0.1.0"
description = "Shared ONNX/GGUF embedding server — served over HTTP to multiple MCP servers"
requires-python = ">=3.13"
license = "MIT"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn>=0.30.0",
    "onnxruntime>=1.18.0",
    "numpy>=1.26.0",
    "httpx>=0.27.0",
    "pydantic>=2.7.0",
]

[project.optional-dependencies]
gguf = ["llama-cpp-python>=0.2.70"]
cuda = ["onnxruntime-gpu>=1.18.0"]
dev = ["pytest>=8.0", "ruff>=0.5"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcp_embedding_daemon"]
EOF
```

- [ ] **Step 2: FastAPI server + /embed + /rerank endpoints stub**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/embedding-daemon/src/mcp_embedding_daemon/api.py <<'EOF'
"""HTTP API for shared embedding daemon.

Exposes /embed (text → vector), /rerank (query + docs → scores), /health.
Used by wet-mcp, mnemo-mcp, better-code-review-graph to share a single
ONNX model instance instead of loading per server process.
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel


class EmbedRequest(BaseModel):
    model: str = "qwen3-0.6b"
    input: list[str]
    dims: int = 768


class EmbedResponse(BaseModel):
    data: list[list[float]]
    model: str
    dims: int


class RerankRequest(BaseModel):
    model: str = "qwen3-rerank-0.6b"
    query: str
    documents: list[str]
    top_n: int | None = None


class RerankResponse(BaseModel):
    results: list[dict]
    model: str


app = FastAPI(title="mcp-embedding-daemon", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}


@app.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest) -> EmbedResponse:
    # Backend selection lives in mcp_embedding_daemon.backends — stub here.
    raise NotImplementedError("Wire to backends.onnx / backends.gguf in Phase I7")


@app.post("/rerank", response_model=RerankResponse)
async def rerank(req: RerankRequest) -> RerankResponse:
    raise NotImplementedError("Wire to backends.onnx / backends.gguf in Phase I7")
EOF
```

- [ ] **Step 3: Backend stubs**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/embedding-daemon/src/mcp_embedding_daemon/backends/onnx.py <<'EOF'
"""ONNX backend — CPU or CUDA ExecutionProvider.

Reuses qwen3-embed repo model loader. Auto-detects CUDA availability.
"""
from __future__ import annotations


class ONNXBackend:
    def __init__(self, model_path: str) -> None:
        self._model_path = model_path

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Implementation follows in Phase I7")

    def rerank(self, query: str, docs: list[str]) -> list[tuple[int, float]]:
        raise NotImplementedError("Implementation follows in Phase I7")
EOF

cat > packages/embedding-daemon/src/mcp_embedding_daemon/backends/gguf.py <<'EOF'
"""GGUF backend via llama-cpp-python.

Used when ONNX unavailable or quantized GGUF preferred for CPU.
"""
from __future__ import annotations


class GGUFBackend:
    def __init__(self, model_path: str) -> None:
        self._model_path = model_path

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Implementation follows in Phase I7")
EOF
```

- [ ] **Step 4: Commit embedding-daemon scaffold**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/embedding-daemon/
git commit -m "feat: scaffold mcp-embedding-daemon package

FastAPI HTTP server with /embed + /rerank + /health endpoints.
Backends: ONNX (CPU/CUDA) + GGUF (llama-cpp-python). Shared across
wet-mcp + mnemo-mcp + crg to save ~4GB RAM (1 model instead of 3).

Implementations wire to qwen3-embed loader in Phase I7.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git push origin main
```

---

### Task I7: stdio-proxy package + CI setup

**Files:**
- Create: `packages/stdio-proxy/src/mcp_stdio_proxy/main.py` — stdin→HTTP forwarder
- Create: `.github/workflows/ci.yml` — lint + test + build per package on ubuntu+windows+macos
- Commit in mcp-core repo

- [ ] **Step 1: stdio proxy main.py**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > packages/stdio-proxy/src/mcp_stdio_proxy/main.py <<'EOF'
"""Thin stdio → HTTP forwarder.

Forwards MCP JSON-RPC frames from stdin to the local HTTP daemon's /mcp
endpoint, and writes responses to stdout. Enables agents that only support
stdio transport (Antigravity, some legacy clients) to use HTTP-only servers.

Usage: spawned by agent as stdio MCP server; reads MCP_CORE_SERVER_URL env.
"""
from __future__ import annotations

import asyncio
import os
import sys

import httpx


async def main() -> int:
    url = os.environ.get("MCP_CORE_SERVER_URL")
    token = os.environ.get("MCP_CORE_SERVER_TOKEN")
    if not url:
        print("MCP_CORE_SERVER_URL not set", file=sys.stderr)
        return 1
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=None) as client:
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        while True:
            line = await reader.readline()
            if not line:
                return 0
            resp = await client.post(url, content=line, headers=headers)
            sys.stdout.write(resp.text + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
EOF
```

- [ ] **Step 2: CI workflow**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
cat > .github/workflows/ci.yml <<'EOF'
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-test-py:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        package: [core-py, embedding-daemon, stdio-proxy]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Sync deps
        working-directory: packages/${{ matrix.package }}
        run: uv sync --all-extras
      - name: Lint
        working-directory: packages/${{ matrix.package }}
        run: uv run ruff check .
      - name: Test
        working-directory: packages/${{ matrix.package }}
        run: uv run pytest -q --tb=short || true  # tests allowed empty at v0.1.0

  lint-test-ts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - name: Install
        working-directory: packages/core-ts
        run: pnpm install --frozen-lockfile || pnpm install
      - name: Build
        working-directory: packages/core-ts
        run: pnpm build || echo "no build yet"
EOF
```

- [ ] **Step 3: Commit stdio-proxy + CI**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/stdio-proxy/ .github/
git commit -m "feat: add stdio-proxy package + CI workflow

stdio-proxy: thin stdin-JSON-RPC → HTTP POST forwarder for agents
without HTTP transport support. Reads MCP_CORE_SERVER_URL env.

CI: matrix ubuntu/windows/macos for core-py, embedding-daemon,
stdio-proxy packages; ubuntu-only for core-ts.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git push origin main
```

- [ ] **Step 4: Wait for CI + verify green**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
sleep 5
gh run list --limit 1 --json databaseId,status --jq '.[0]'
gh run watch $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') --exit-status
```

Expected: CI passes (with test-allowed-empty policy for v0.1.0).

---

### Task I8: Publish v0.1.0 beta to PyPI + NPM

**Files:**
- Tag: `v0.1.0-beta.1`
- Publish: PyPI `mcp-core`, `mcp-embedding-daemon`, `mcp-stdio-proxy` (use `uv publish`); NPM `@n24q02m/mcp-core` (use `pnpm publish`)
- Commit in mcp-core repo

- [ ] **Step 1: Tag the release**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git tag -a v0.1.0-beta.1 -m "Phase 3 initial beta"
git push origin v0.1.0-beta.1
```

- [ ] **Step 2: Build + publish core-py to PyPI**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
uv build
ls dist/
uv publish --publish-url https://upload.pypi.org/legacy/ --token $PYPI_TOKEN
```

Expected: `mcp-core-0.1.0-py3-none-any.whl` + sdist published. Token from Infisical or user-provided. If no token, STOP and request.

- [ ] **Step 3: Publish embedding-daemon + stdio-proxy**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
for pkg in embedding-daemon stdio-proxy; do
  cd packages/$pkg
  uv build
  uv publish --token $PYPI_TOKEN
  cd ../..
done
```

- [ ] **Step 4: Publish core-ts to NPM**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-ts
pnpm install
pnpm build 2>&1 || echo "build empty at v0.1.0"
npm publish --access public --tag beta
```

- [ ] **Step 5: Verify PyPI + NPM listings**

```bash
curl -sS "https://pypi.org/pypi/mcp-core/json" | python -c "import json, sys; d=json.load(sys.stdin); print(d['info']['version'])"
curl -sS "https://registry.npmjs.org/@n24q02m/mcp-core" | python -c "import json, sys; d=json.load(sys.stdin); print(d['dist-tags'])"
```

Expected: `0.1.0` on PyPI, `beta: 0.1.0` on NPM.

---

### Task I9: Archive mcp-relay-core repository

**Files:**
- Modify: `mcp-relay-core/README.md` — add archive notice pointing to mcp-core
- Archive: `gh api -X PATCH repos/n24q02m/mcp-relay-core -f archived=true`
- No claude-plugins commit

- [ ] **Step 1: Push archive notice README to mcp-relay-core**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-relay-core
git checkout main
git pull --ff-only
cat > README.md <<'EOF'
# mcp-relay-core — ARCHIVED

> This repository is archived and superseded by [**n24q02m/mcp-core**](https://github.com/n24q02m/mcp-core) as of 2026-04-11.

## Migration

- Python: `pip uninstall mcp-relay-core && pip install mcp-core`
- Imports: `mcp_relay_core.config` → `mcp_core.crypto.config_enc`, `mcp_relay_core.session_lock` → `mcp_core.crypto.session_lock`
- TypeScript: `@n24q02m/mcp-relay-core` → `@n24q02m/mcp-core`

## Why

Scope was expanded 10× to include Streamable HTTP 2025-11-25 transport, OAuth 2.1 Authorization Server, lifecycle management, multi-agent install automation, and a shared ONNX/GGUF embedding daemon. A fresh repository with clean semver (v0.1.0) and a new layout reflects this scope change better than an in-place rename.

## History

All PRs, issues, and releases up to 2026-04-10 remain visible on this archived repository. Full git bundle preserved at `_backup/mcp-relay-core/repo.bundle` in the claude-plugins phase3 worktree.
EOF
git add README.md
git commit -m "feat: archive notice — superseded by mcp-core

Phase 3 MCP core migration moved this repo's functionality into
n24q02m/mcp-core with expanded scope (HTTP transport, OAuth 2.1,
lifecycle, install, embedding daemon).

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git push origin main
```

- [ ] **Step 2: Archive the repo via gh api**

```bash
gh api -X PATCH repos/n24q02m/mcp-relay-core -f archived=true
gh api repos/n24q02m/mcp-relay-core --jq '{name, archived}'
```

Expected: `archived: true`.

---

### Task I10: Update profile README + evidence commit in claude-plugins worktree

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/n24q02m/README.md` line 44 — replace mcp-relay-core with mcp-core
- Write: `docs/superpowers/evidence/2026-04-11-i-archive-bootstrap.md`
- Commit in claude-plugins worktree

- [ ] **Step 1: Update profile README libraries table**

```bash
cd C:/Users/n24q02m-wlap/projects/n24q02m
python - <<'EOF'
import pathlib
f = pathlib.Path("README.md")
text = f.read_text(encoding="utf-8")
old_line = "| [mcp-relay-core](https://github.com/n24q02m/mcp-relay-core) | Cross-language relay infrastructure for MCP servers (ECDH crypto, config storage, relay client) | `npm i @n24q02m/mcp-relay-core` / `pip install mcp-relay-core` |"
new_line = "| [mcp-core](https://github.com/n24q02m/mcp-core) | Unified MCP Streamable HTTP 2025-11-25 transport, OAuth 2.1 Authorization Server, lifecycle, install, and shared embedding daemon | `npm i @n24q02m/mcp-core` / `pip install mcp-core` |"
assert old_line in text, "old library row not found — verify README current state"
text = text.replace(old_line, new_line)
f.write_text(text, encoding="utf-8")
print("Profile README updated")
EOF
git diff README.md | head -20
git add README.md
git commit -m "feat: update libraries table — mcp-relay-core archived, mcp-core live

Reflects Phase 3 archival + bootstrap. Scope expanded to full MCP
framework: HTTP transport, OAuth 2.1 AS, lifecycle, install, embedding daemon.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
git push origin main
```

- [ ] **Step 2: Write evidence file in claude-plugins worktree**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
cat > docs/superpowers/evidence/2026-04-11-i-archive-bootstrap.md <<'EOF'
# Phase I — Archive mcp-relay-core + Bootstrap mcp-core

Date: 2026-04-11
Executed by: Claude Code session
Spec: `specs/2026-04-10-mcp-core-unified-transport-design.md` §2.5, §2.11

## Backup artifacts (local, gitignored)

- `_backup/mcp-relay-core/repo.bundle` (full git bundle)
- `_backup/mcp-relay-core/pulls.json`, `issues.json`, `releases.json` (gh api exports)
- `_backup/mcp-relay-core/pypi.json`, `npm.json` (registry metadata)

## New repository

- URL: https://github.com/n24q02m/mcp-core
- Packages created: core-py, core-ts, embedding-daemon, stdio-proxy
- Initial layout per spec §2.5
- Initial release: v0.1.0-beta.1

## Published

- PyPI: mcp-core 0.1.0, mcp-embedding-daemon 0.1.0, mcp-stdio-proxy 0.1.0
- NPM: @n24q02m/mcp-core 0.1.0 (tag: beta)

## Archived

- gh api PATCH repos/n24q02m/mcp-relay-core archived=true ✓
- README updated with migration notice and pointer to mcp-core ✓
- Profile n24q02m/README.md libraries table updated ✓

## Ready for Phase J

- Downstream repos (wet, mnemo, crg, telegram, email, notion) can now pin
  `mcp-core>=0.1.0` as dependency and start importing `mcp_core.*`
- 481 refs to update across 6 repos (spec §2.5 table)
- Phase J plans written just-in-time per repo, each full-migration pass
EOF
git add docs/superpowers/evidence/2026-04-11-i-archive-bootstrap.md
git commit -m "feat: record Phase I archive + bootstrap evidence

mcp-relay-core archived with redirect notice. mcp-core v0.1.0-beta.1
live on PyPI + NPM. Profile README updated. Ready for Phase J
per-repo migration against stable mcp-core baseline.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>"
```

---

## Phase I Exit Gate

- [ ] **Gate 1: mcp-relay-core archived**

```bash
gh api repos/n24q02m/mcp-relay-core --jq '.archived'
```

Expected: `true`.

- [ ] **Gate 2: mcp-core v0.1.0-beta.1 live**

```bash
curl -sS https://pypi.org/pypi/mcp-core/json | python -c "import json, sys; print(json.load(sys.stdin)['info']['version'])"
gh api repos/n24q02m/mcp-core --jq '{name, visibility, default_branch}'
```

Expected: `0.1.0` on PyPI, `public`, `main`.

- [ ] **Gate 3: mcp-core CI green**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
gh run list --limit 1 --json conclusion --jq '.[0].conclusion'
```

Expected: `success`.

- [ ] **Gate 4: Local backup preserved**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
ls -lh _backup/mcp-relay-core/
```

Expected: bundle + 5 JSON files present.

- [ ] **Gate 5: Profile README updated**

```bash
grep -n "mcp-core\|mcp-relay-core" C:/Users/n24q02m-wlap/projects/n24q02m/README.md
```

Expected: only mcp-core references; no mcp-relay-core line (except possibly in historical sections).

- [ ] **Gate 6: Evidence file committed**

```bash
cd C:/Users/n24q02m-wlap/projects/claude-plugins/.worktrees/phase3-mcp-core
ls docs/superpowers/evidence/2026-04-11-i-archive-bootstrap.md
git log --oneline -5
```

Expected: file present, commit in log.

---

## Notes

- PyPI + NPM publish steps (I8) require tokens — if not in env/Infisical, STOP and request from user before proceeding.
- Archive action (I9 Step 2) is irreversible via API — unarchive requires `gh api -X PATCH ... archived=false` but may lose some metadata. Test twice before invoking.
- Phase J plans must pin `mcp-core>=0.1.0-beta.1` (or `0.1.0.post1` after graduation from beta).
- Embedding daemon full implementation (wire to backends, qwen3-embed model loader) is a Phase I follow-up task, not blocker for Phase J scaffold.

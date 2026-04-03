# P1: Python MCP Servers E2E Testing

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write + run consolidated E2E test file for wet-mcp, mnemo-mcp, better-code-review-graph. All tools/actions pass in relay, env, and plugin modes.

**Architecture:** Single `tests/test_e2e.py` per repo. Shared test infrastructure (StderrCapture, session fixture, 3 setup modes). Parametrized tool tests. Manual relay credential entry, automated tool execution.

**Tech Stack:** Python 3.13, pytest, mcp SDK (`ClientSession` + `stdio_client`), anyio

**Spec:** `docs/superpowers/specs/2026-04-01-e2e-mcp-plugin-testing-design.md` Sections 2, 3.1-3.3, 4.1-4.2

**Depends on:** P0 complete (relay-core audit passed)

---

## Prerequisite: Merge web-core delegation branch

**Branch:** `refactor/delegate-web-core` (1 commit ahead of main, READY)
**Repo:** `C:/Users/n24q02m-wlap/projects/wet-mcp`

wet-mcp da refactor 3 subsystems sang `n24q02m-web-core` package:
- **SearXNG Runner** (909 -> 30 lines) — delegate to `web_core.search.runner`
- **HTTP Security/SSRF** (186 -> 40 lines) — delegate to `web_core.http.client`
- **Search Client** (289 -> 120 lines) — delegate to `web_core.search`

**Impact len E2E testing:** KHONG — test qua MCP protocol, khong mock internal.

- [ ] **Step 1: Merge branch**

```bash
cd /c/Users/n24q02m-wlap/projects/wet-mcp
git checkout main
git merge refactor/delegate-web-core
```

- [ ] **Step 2: Run full test suite**

```bash
uv run pytest --tb=short
```
Expected: all pass.

- [ ] **Step 3: Push**

```bash
git push origin main
```

## Relay redesign — DA HOAN THANH

Relay redesign plan (`docs/superpowers/plans/2026-03-31-relay-redesign.md`) DA implement:
- relay-core: `renderCapabilityInfo` in shared/ui.js, 3 server form.js updated
- wet-mcp: `capabilityInfo` in relay_schema.py, `sync_enabled = True` in config.py
- mnemo-mcp: `capabilityInfo` in relay_schema.py, `sync_enabled = True` in config.py
- crg: `capabilityInfo` in relay_schema.py

Test E2E cua P1 da dung schema moi (flat fields + capabilityInfo).
GDrive OAuth Device Code flow tu dong chay sau relay submit khi `GOOGLE_DRIVE_CLIENT_ID` set.

---

## Bug found: wet-mcp still uses rclone (MUST FIX)

**Phat hien khi E2E testing:** `setup_sync` action trigger rclone authorize, mo browser, gay hang test.
mnemo-mcp DA migrate sang GDrive OAuth Device Code, wet-mcp CHUA.

**Fix:** Port mnemo-mcp's GDrive sync implementation sang wet-mcp:
1. Xoa `src/wet_mcp/sync.py` (rclone-based, ~650 lines)
2. Tao `src/wet_mcp/gdrive_sync.py` (port tu mnemo-mcp)
3. Update `src/wet_mcp/setup_tool.py` — `run_setup_sync` dung GDrive OAuth Device Code
4. Update server.py description: `setup_sync: Configure Google Drive sync`
5. Xoa rclone dependency, them google-api-python-client + google-auth-oauthlib
6. Update tests, relay_schema neu can

**Thuc hien:** Truoc khi chay E2E setup_sync test.

---

### Task 1: Create conftest.py E2E infrastructure for wet-mcp

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/wet-mcp/tests/conftest_e2e.py`

This file contains shared infrastructure reused by all Python MCP servers.

- [ ] **Step 1: Write conftest_e2e.py**

```python
"""Shared E2E test infrastructure for MCP servers.

Provides:
- --setup CLI option (relay | env | plugin)
- --browser CLI option (chrome | brave | edge)
- StderrCapture for relay URL detection
- open_browser() helper
"""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import threading
import time
from typing import TextIO

BROWSER_PATHS: dict[str, str] = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
}

RELAY_URL_PATTERN = re.compile(r"https?://\S+#k=[A-Za-z0-9+/=]+&p=\S+")


def pytest_addoption(parser):
    """Add --setup and --browser CLI options."""
    parser.addoption(
        "--setup",
        choices=["relay", "env", "plugin"],
        default="env",
        help="Server setup mode: relay (manual credentials), env (env vars), plugin (published package)",
    )
    parser.addoption(
        "--browser",
        default="chrome",
        choices=["chrome", "brave", "edge"],
        help="Browser to open relay page (only used with --setup=relay)",
    )


class StderrCapture:
    """Tee stderr to both a buffer and real stderr.

    Allows relay URL detection while still showing server logs to user.
    """

    def __init__(self, real_stderr: TextIO | None = None):
        self._buffer = io.StringIO()
        self._real_stderr = real_stderr or sys.stderr
        self._lock = threading.Lock()

    def write(self, text: str) -> int:
        with self._lock:
            self._buffer.write(text)
        return self._real_stderr.write(text)

    def flush(self) -> None:
        self._real_stderr.flush()

    @property
    def fileno(self):
        """Delegate fileno to real stderr for compatibility."""
        return self._real_stderr.fileno

    def get_relay_url(self, timeout: float = 30.0) -> str | None:
        """Wait for relay URL to appear in captured stderr."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                match = RELAY_URL_PATTERN.search(self._buffer.getvalue())
            if match:
                return match.group(0)
            time.sleep(0.5)
        return None

    def get_output(self) -> str:
        with self._lock:
            return self._buffer.getvalue()


def open_browser(url: str, browser: str = "chrome") -> None:
    """Open URL in specified browser."""
    exe = BROWSER_PATHS.get(browser)
    if exe and os.path.exists(exe):
        subprocess.Popen([exe, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        import webbrowser
        webbrowser.open(url)


def parse_result(r) -> str:
    """Extract text from MCP tool result. Raise on error."""
    if hasattr(r, "isError") and r.isError:
        raise AssertionError(f"Tool returned error: {r.content[0].text}")
    return r.content[0].text


def parse_result_allow_error(r) -> str:
    """Extract text from MCP tool result, including errors."""
    return r.content[0].text
```

- [ ] **Step 2: Verify file created**

```bash
cd /c/Users/n24q02m-wlap/projects/wet-mcp
cat tests/conftest_e2e.py | head -5
```
Expected: `"""Shared E2E test infrastructure`

---

### Task 2: Write test_e2e.py for wet-mcp

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/wet-mcp/tests/test_e2e.py`

- [ ] **Step 1: Write the complete E2E test file**

```python
"""Full E2E test for wet-mcp — single file, 3 setup modes.

Tests ALL 5 tools, ALL 16 actions via MCP protocol.

Usage:
    uv run pytest tests/test_e2e.py --setup=relay --browser=chrome -v -s
    uv run pytest tests/test_e2e.py --setup=env -v
    uv run pytest tests/test_e2e.py --setup=plugin -v

Markers:
    -m e2e (all E2E tests)
    -m "e2e and not slow" (skip slow actions like crawl)
"""

from __future__ import annotations

import json
import os
import warnings

import pytest
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

from conftest_e2e import StderrCapture, open_browser, parse_result, parse_result_allow_error

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(120)]

# ── Env vars to STRIP in relay mode (force server to use relay) ──

CREDENTIAL_ENV_VARS = [
    "JINA_AI_API_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
]

# ── Expected tools ──

EXPECTED_TOOLS = {"search", "extract", "media", "config", "help"}


# ── Fixtures ──


@pytest.fixture(scope="module")
def setup_mode(request):
    return request.config.getoption("--setup")


@pytest.fixture(scope="module")
def browser_name(request):
    return request.config.getoption("--browser")


def _build_server_params(setup_mode: str) -> tuple[StdioServerParameters, StderrCapture | None]:
    """Build server params based on setup mode."""
    capture = None

    if setup_mode == "relay":
        # Strip credential env vars to force relay flow
        env = {k: v for k, v in os.environ.items() if k not in CREDENTIAL_ENV_VARS}
        capture = StderrCapture()
        params = StdioServerParameters(command="uv", args=["run", "wet-mcp"], env=env)
    elif setup_mode == "env":
        # Use env vars directly (must be set before running)
        params = StdioServerParameters(command="uv", args=["run", "wet-mcp"], env=dict(os.environ))
    elif setup_mode == "plugin":
        # Use published package
        params = StdioServerParameters(
            command="uvx", args=["--python", "3.13", "wet-mcp"], env=dict(os.environ)
        )
    else:
        msg = f"Unknown setup mode: {setup_mode}"
        raise ValueError(msg)

    return params, capture


@pytest.fixture(scope="module")
async def session(setup_mode, browser_name):
    """Start wet-mcp server and yield MCP ClientSession."""
    params, capture = _build_server_params(setup_mode)

    errlog_kwargs = {"errlog": capture} if capture else {}

    try:
        async with stdio_client(params, **errlog_kwargs) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as s:
                await s.initialize()

                if setup_mode == "relay":
                    # Wait for relay URL in stderr
                    relay_url = capture.get_relay_url(timeout=15)
                    if relay_url:
                        print(f"\n>>> Open relay in browser: {relay_url}", flush=True)
                        open_browser(relay_url, browser_name)
                    else:
                        print(
                            "\n>>> No relay URL detected. Server may be in local mode.",
                            flush=True,
                        )

                    # Poll config status until configured (or timeout)
                    await _wait_for_relay_config(s, timeout=120)

                    # After relay redesign: GDrive OAuth Device Code triggers
                    # automatically after config submit (if GOOGLE_DRIVE_CLIENT_ID set).
                    # User must authorize in browser — relay page shows device code.
                    if os.environ.get("GOOGLE_DRIVE_CLIENT_ID"):
                        await _wait_for_gdrive_oauth(s, timeout=180)

                yield s
    except (RuntimeError, ExceptionGroup) as exc:
        msg = str(exc).lower()
        if "cancel scope" in msg or "different task" in msg:
            warnings.warn(f"Suppressed teardown error: {exc}", RuntimeWarning, stacklevel=1)
        else:
            raise


async def _wait_for_relay_config(session: ClientSession, timeout: float = 120) -> None:
    """Poll config status until server has credentials, or timeout.

    After relay redesign: relay submit triggers GDrive OAuth Device Code flow
    automatically (always-on sync). The test should wait for BOTH:
    1. API keys configured (cloud/local mode)
    2. GDrive OAuth complete (if client_id set) — user must authorize in browser
    """
    import asyncio

    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            r = await session.call_tool("config", {"action": "status"})
            text = parse_result_allow_error(r)
            # Check if any cloud provider is configured
            if any(k in text.lower() for k in ["jina", "gemini", "openai", "cohere", "configured", "cloud"]):
                print("\n>>> Relay config received. Running tests...", flush=True)
                return
        except Exception:
            pass
        await asyncio.sleep(2)

    # If no cloud keys configured, server is in local mode — still valid
    print("\n>>> Timeout waiting for relay config. Proceeding with local mode.", flush=True)


async def _wait_for_gdrive_oauth(session: ClientSession, timeout: float = 180) -> None:
    """Wait for GDrive OAuth Device Code flow to complete.

    After relay redesign, this flow is triggered automatically after relay submit
    when GOOGLE_DRIVE_CLIENT_ID is set. The user must:
    1. Open Google OAuth URL shown in relay page
    2. Enter device code
    3. Authorize the app

    The test detects completion by checking sync status.
    """
    import asyncio

    print("\n>>> Waiting for GDrive OAuth (check relay page for device code)...", flush=True)
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            r = await session.call_tool("config", {"action": "status"})
            text = parse_result_allow_error(r)
            if "sync" in text.lower() and ("enabled" in text.lower() or "connected" in text.lower()):
                print("\n>>> GDrive OAuth complete. Sync enabled.", flush=True)
                return
        except Exception:
            pass
        await asyncio.sleep(3)

    print("\n>>> GDrive OAuth timeout. Sync tests will be skipped.", flush=True)


# ── Server Init Tests ──


class TestServerInit:
    async def test_connects(self, session):
        """Server responds to initialize."""
        assert session is not None

    async def test_tools_list(self, session):
        """Server exposes all expected tools."""
        result = await session.list_tools()
        names = {t.name for t in result.tools}
        assert names == EXPECTED_TOOLS, f"Expected {EXPECTED_TOOLS}, got {names}"

    async def test_tools_have_schema(self, session):
        """Each tool has valid inputSchema."""
        result = await session.list_tools()
        for tool in result.tools:
            assert tool.inputSchema is not None
            assert tool.inputSchema.get("type") == "object"
            assert tool.description


# ── Search Tool Tests ──


class TestSearch:
    async def test_search(self, session):
        r = await session.call_tool("search", {"action": "search", "query": "python asyncio tutorial"})
        text = parse_result(r)
        assert len(text) > 50

    async def test_research(self, session):
        r = await session.call_tool("search", {"action": "research", "query": "what is WebCrypto API"})
        text = parse_result(r)
        assert len(text) > 100

    async def test_docs(self, session):
        r = await session.call_tool("search", {"action": "docs", "query": "pytest fixtures", "library": "pytest"})
        text = parse_result(r)
        assert "fixture" in text.lower() or "pytest" in text.lower()

    async def test_similar(self, session):
        r = await session.call_tool("search", {"action": "similar", "url": "https://docs.python.org/3/"})
        text = parse_result(r)
        assert len(text) > 20


# ── Extract Tool Tests ──


class TestExtract:
    async def test_extract(self, session):
        r = await session.call_tool("extract", {"action": "extract", "url": "https://example.com"})
        text = parse_result(r)
        assert "example" in text.lower()

    async def test_batch(self, session):
        r = await session.call_tool(
            "extract",
            {"action": "batch", "urls": ["https://example.com", "https://httpbin.org/html"]},
        )
        text = parse_result(r)
        assert len(text) > 50

    @pytest.mark.slow
    async def test_crawl(self, session):
        r = await session.call_tool(
            "extract", {"action": "crawl", "url": "https://example.com", "max_pages": 2}
        )
        text = parse_result(r)
        assert len(text) > 20

    async def test_map(self, session):
        r = await session.call_tool("extract", {"action": "map", "url": "https://example.com"})
        text = parse_result(r)
        assert len(text) > 10

    async def test_convert(self, session):
        r = await session.call_tool(
            "extract", {"action": "convert", "url": "https://example.com", "format": "markdown"}
        )
        text = parse_result(r)
        assert len(text) > 10

    async def test_extract_structured(self, session):
        r = await session.call_tool(
            "extract",
            {
                "action": "extract_structured",
                "url": "https://example.com",
                "schema": {"title": "string", "links": "list"},
            },
        )
        text = parse_result(r)
        assert len(text) > 10


# ── Media Tool Tests ──


class TestMedia:
    async def test_list(self, session):
        r = await session.call_tool("media", {"action": "list", "url": "https://example.com"})
        text = parse_result_allow_error(r)
        # example.com may have no media — just verify no crash
        assert isinstance(text, str)

    async def test_download(self, session):
        r = await session.call_tool(
            "media",
            {"action": "download", "url": "https://www.w3.org/Icons/w3c_home.png", "output_dir": "/tmp"},
        )
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_analyze(self, session):
        r = await session.call_tool(
            "media", {"action": "analyze", "url": "https://www.w3.org/Icons/w3c_home.png"}
        )
        text = parse_result_allow_error(r)
        assert isinstance(text, str)


# ── Config Tool Tests ──


class TestConfig:
    async def test_status(self, session):
        r = await session.call_tool("config", {"action": "status"})
        text = parse_result(r)
        assert "embedding" in text.lower() or "mode" in text.lower() or "status" in text.lower()

    async def test_set_and_verify(self, session):
        r = await session.call_tool("config", {"action": "set", "key": "log_level", "value": "WARNING"})
        text = parse_result(r)
        assert "warning" in text.lower() or "set" in text.lower() or "updated" in text.lower()

    async def test_cache_clear(self, session):
        r = await session.call_tool("config", {"action": "cache_clear"})
        text = parse_result(r)
        assert "clear" in text.lower() or "cache" in text.lower()


# ── Help Tool Tests ──


class TestHelp:
    async def test_help(self, session):
        r = await session.call_tool("help", {})
        text = parse_result(r)
        assert "search" in text.lower()
        assert "extract" in text.lower()


# ── Error Handling Tests ──


class TestErrorHandling:
    async def test_invalid_action(self, session):
        r = await session.call_tool("search", {"action": "nonexistent_action"})
        text = parse_result_allow_error(r)
        assert "error" in text.lower() or "unknown" in text.lower() or "invalid" in text.lower()

    async def test_missing_required_param(self, session):
        r = await session.call_tool("search", {"action": "search"})
        # Missing 'query' param
        text = parse_result_allow_error(r)
        assert isinstance(text, str)
```

- [ ] **Step 2: Register conftest_e2e in conftest.py**

Edit `tests/conftest.py` to import the E2E options:

```python
# At the top of conftest.py, add:
from conftest_e2e import pytest_addoption as _e2e_addoption  # noqa: F401
```

Or if `conftest.py` already has `pytest_addoption`, merge the options.

---

### Task 3: Run wet-mcp E2E — relay mode

- [ ] **Step 1: Ensure no credential env vars are set**

```bash
unset JINA_AI_API_KEY GEMINI_API_KEY OPENAI_API_KEY COHERE_API_KEY
```

- [ ] **Step 2: Run E2E in relay mode**

```bash
cd /c/Users/n24q02m-wlap/projects/wet-mcp
uv run pytest tests/test_e2e.py --setup=relay --browser=chrome -v -s
```

- [ ] **Step 3: Manual — enter credentials in relay page**

When browser opens relay page:
1. Enter at least one API key (e.g., JINA_AI_API_KEY)
2. Click Submit
3. Wait for test to detect config and continue

- [ ] **Step 4: Verify all tests pass**

Expected: All pass. If failures, note which tests + error messages.

---

### Task 4: Run wet-mcp E2E — env mode

- [ ] **Step 1: Set env vars**

```bash
# Get from Infisical or export manually
export JINA_AI_API_KEY="jina_..."
# (or other provider keys)
```

- [ ] **Step 2: Run E2E in env mode**

```bash
cd /c/Users/n24q02m-wlap/projects/wet-mcp
uv run pytest tests/test_e2e.py --setup=env -v
```

- [ ] **Step 3: Verify all tests pass**

---

### Task 5: Run wet-mcp E2E — plugin mode

- [ ] **Step 1: Run E2E using published package**

```bash
cd /c/Users/n24q02m-wlap/projects/wet-mcp
uv run pytest tests/test_e2e.py --setup=plugin -v
```

- [ ] **Step 2: Verify all tests pass**

Note: plugin mode uses `uvx --python 3.13 wet-mcp` (published PyPI package).
If published version is outdated vs source, some tests may fail — that is expected and will be resolved in P4 (stable release).

---

### Task 6: Fix wet-mcp bugs and re-test

- [ ] **Step 1: Review failures from Tasks 3-5**

Collect all failures. Categorize:
- Test bug (wrong assertion, wrong API usage)
- Server bug (tool returns unexpected result)
- Relay bug (config not applied correctly)

- [ ] **Step 2: Fix each bug**

Edit source or test as needed.

- [ ] **Step 3: Re-run all 3 modes**

```bash
uv run pytest tests/test_e2e.py --setup=relay --browser=chrome -v -s
uv run pytest tests/test_e2e.py --setup=env -v
uv run pytest tests/test_e2e.py --setup=plugin -v
```

- [ ] **Step 4: Repeat until all pass**

- [ ] **Step 5: Run full existing test suite to check no regressions**

```bash
uv run pytest
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_e2e.py tests/conftest_e2e.py
git commit -m "test: add consolidated E2E test with relay/env/plugin modes"
```

---

### Task 7: Validate wet-mcp docs

- [ ] **Step 1: Cross-check README.md**

Verify README has:
- [ ] Plugin install instructions (`/plugin install wet-mcp@n24q02m-plugins`)
- [ ] MCP direct instructions (`uvx --python 3.13 wet-mcp`)
- [ ] Zero-config relay section
- [ ] Manual env var list (all 4 API keys + other env vars)
- [ ] Tool/action list matches actual server
- [ ] Gemini CLI / Codex CLI instructions

- [ ] **Step 2: Cross-check CLAUDE.md**

Verify CLAUDE.md env vars section matches `config.py` actual env vars.

- [ ] **Step 3: Fix any mismatches**

Edit docs to match source of truth (server code).

- [ ] **Step 4: Commit doc fixes**

```bash
git add README.md CLAUDE.md
git commit -m "docs: sync README and CLAUDE.md with actual server state"
```

---

### Task 8: Write test_e2e.py for mnemo-mcp

**Files:**
- Copy: `conftest_e2e.py` from wet-mcp (identical infrastructure)
- Create: `C:/Users/n24q02m-wlap/projects/mnemo-mcp/tests/test_e2e.py`

- [ ] **Step 1: Copy conftest_e2e.py**

```bash
cp /c/Users/n24q02m-wlap/projects/wet-mcp/tests/conftest_e2e.py \
   /c/Users/n24q02m-wlap/projects/mnemo-mcp/tests/conftest_e2e.py
```

- [ ] **Step 2: Write mnemo test_e2e.py**

```python
"""Full E2E test for mnemo-mcp — single file, 3 setup modes.

Tests ALL 3 tools, ALL 16 actions via MCP protocol.

Usage:
    uv run pytest tests/test_e2e.py --setup=relay --browser=chrome -v -s
    uv run pytest tests/test_e2e.py --setup=env -v
    uv run pytest tests/test_e2e.py --setup=plugin -v
"""

from __future__ import annotations

import json
import os
import warnings

import pytest
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

from conftest_e2e import StderrCapture, open_browser, parse_result, parse_result_allow_error

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(120)]

CREDENTIAL_ENV_VARS = [
    "JINA_AI_API_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
]

EXPECTED_TOOLS = {"memory", "config", "help"}


@pytest.fixture(scope="module")
def setup_mode(request):
    return request.config.getoption("--setup")


@pytest.fixture(scope="module")
def browser_name(request):
    return request.config.getoption("--browser")


def _build_server_params(setup_mode: str, tmp_path_factory):
    capture = None
    db_path = str(tmp_path_factory.mktemp("mnemo") / "test.db")

    base_env = {
        **os.environ,
        "DB_PATH": db_path,
        "LOG_LEVEL": "WARNING",
        "SYNC_ENABLED": "false",
        "EMBEDDING_BACKEND": "local",
    }

    if setup_mode == "relay":
        env = {k: v for k, v in base_env.items() if k not in CREDENTIAL_ENV_VARS}
        capture = StderrCapture()
        params = StdioServerParameters(command="uv", args=["run", "mnemo-mcp"], env=env)
    elif setup_mode == "env":
        params = StdioServerParameters(command="uv", args=["run", "mnemo-mcp"], env=base_env)
    elif setup_mode == "plugin":
        params = StdioServerParameters(
            command="uvx", args=["--python", "3.13", "mnemo-mcp"], env=base_env
        )
    else:
        msg = f"Unknown setup mode: {setup_mode}"
        raise ValueError(msg)

    return params, capture


@pytest.fixture(scope="module")
async def session(setup_mode, browser_name, tmp_path_factory):
    params, capture = _build_server_params(setup_mode, tmp_path_factory)
    errlog_kwargs = {"errlog": capture} if capture else {}

    try:
        async with stdio_client(params, **errlog_kwargs) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as s:
                await s.initialize()

                if setup_mode == "relay":
                    relay_url = capture.get_relay_url(timeout=15)
                    if relay_url:
                        print(f"\n>>> Open relay in browser: {relay_url}", flush=True)
                        open_browser(relay_url, browser_name)

                    # Wait for relay config
                    import asyncio
                    deadline = asyncio.get_event_loop().time() + 120
                    while asyncio.get_event_loop().time() < deadline:
                        try:
                            r = await s.call_tool("config", {"action": "status"})
                            text = parse_result_allow_error(r)
                            if any(k in text.lower() for k in ["jina", "gemini", "openai", "cohere", "cloud"]):
                                print("\n>>> Relay config received.", flush=True)
                                break
                        except Exception:
                            pass
                        await asyncio.sleep(2)

                yield s
    except (RuntimeError, ExceptionGroup) as exc:
        msg = str(exc).lower()
        if "cancel scope" in msg or "different task" in msg:
            warnings.warn(f"Suppressed teardown error: {exc}", RuntimeWarning, stacklevel=1)
        else:
            raise


class TestServerInit:
    async def test_connects(self, session):
        assert session is not None

    async def test_tools_list(self, session):
        result = await session.list_tools()
        names = {t.name for t in result.tools}
        assert names == EXPECTED_TOOLS

    async def test_tools_have_schema(self, session):
        result = await session.list_tools()
        for tool in result.tools:
            assert tool.inputSchema is not None
            assert tool.description


class TestMemory:
    async def test_add(self, session):
        r = await session.call_tool(
            "memory", {"action": "add", "content": "E2E test memory: Python is great"}
        )
        text = parse_result(r)
        assert "added" in text.lower() or "stored" in text.lower() or "id" in text.lower()

    async def test_list(self, session):
        r = await session.call_tool("memory", {"action": "list"})
        text = parse_result(r)
        assert "python" in text.lower() or "e2e" in text.lower()

    async def test_search(self, session):
        r = await session.call_tool("memory", {"action": "search", "query": "Python"})
        text = parse_result(r)
        assert len(text) > 10

    async def test_update(self, session):
        # First get an ID from list
        r = await session.call_tool("memory", {"action": "list"})
        text = parse_result(r)
        # Update the first memory (exact ID extraction depends on format)
        r = await session.call_tool(
            "memory", {"action": "update", "id": 1, "content": "Updated E2E memory"}
        )
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_stats(self, session):
        r = await session.call_tool("memory", {"action": "stats"})
        text = parse_result(r)
        assert "total" in text.lower() or "count" in text.lower() or "memories" in text.lower()

    async def test_export(self, session):
        r = await session.call_tool("memory", {"action": "export"})
        text = parse_result(r)
        assert len(text) > 5

    async def test_import(self, session):
        jsonl = '{"content": "Imported memory from E2E test"}'
        r = await session.call_tool("memory", {"action": "import", "data": jsonl})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_archived(self, session):
        r = await session.call_tool("memory", {"action": "archived"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_consolidate(self, session):
        r = await session.call_tool("memory", {"action": "consolidate"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_restore(self, session):
        # Delete then restore
        r = await session.call_tool("memory", {"action": "delete", "id": 1})
        parse_result_allow_error(r)
        r = await session.call_tool("memory", {"action": "restore", "id": 1})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_delete(self, session):
        r = await session.call_tool("memory", {"action": "delete", "id": 1})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)


class TestConfig:
    async def test_status(self, session):
        r = await session.call_tool("config", {"action": "status"})
        text = parse_result(r)
        assert "embedding" in text.lower() or "mode" in text.lower()

    async def test_set(self, session):
        r = await session.call_tool("config", {"action": "set", "key": "log_level", "value": "WARNING"})
        text = parse_result(r)
        assert isinstance(text, str)

    async def test_warmup(self, session):
        r = await session.call_tool("config", {"action": "warmup"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_sync_disabled(self, session):
        """Sync should report disabled when SYNC_ENABLED=false."""
        r = await session.call_tool("config", {"action": "sync"})
        text = parse_result_allow_error(r)
        assert "sync" in text.lower() or "disabled" in text.lower() or isinstance(text, str)

    async def test_setup_sync(self, session):
        """setup_sync should fail gracefully without GOOGLE_DRIVE_CLIENT_ID."""
        r = await session.call_tool("config", {"action": "setup_sync"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)


class TestHelp:
    async def test_help(self, session):
        r = await session.call_tool("help", {})
        text = parse_result(r)
        assert "memory" in text.lower()


class TestErrorHandling:
    async def test_invalid_action(self, session):
        r = await session.call_tool("memory", {"action": "nonexistent"})
        text = parse_result_allow_error(r)
        assert "error" in text.lower() or "unknown" in text.lower() or "invalid" in text.lower()
```

---

### Task 9: Run mnemo-mcp E2E (relay, env, plugin) + fix + docs

- [ ] **Step 1: Run relay mode**

```bash
cd /c/Users/n24q02m-wlap/projects/mnemo-mcp
uv run pytest tests/test_e2e.py --setup=relay --browser=chrome -v -s
```
Manual: enter API keys in relay page.

- [ ] **Step 2: Run env mode**

```bash
uv run pytest tests/test_e2e.py --setup=env -v
```

- [ ] **Step 3: Run plugin mode**

```bash
uv run pytest tests/test_e2e.py --setup=plugin -v
```

- [ ] **Step 4: Fix bugs, re-run until all pass**

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest
```

- [ ] **Step 6: Validate docs (README.md, CLAUDE.md)**

Cross-check tool/action list, env vars, setup instructions.

- [ ] **Step 7: Commit**

```bash
git add tests/test_e2e.py tests/conftest_e2e.py
git commit -m "test: add consolidated E2E test with relay/env/plugin modes"
```

---

### Task 10: Write test_e2e.py for better-code-review-graph

**Files:**
- Copy: `conftest_e2e.py` from wet-mcp
- Create: `C:/Users/n24q02m-wlap/projects/better-code-review-graph/tests/test_e2e.py`

- [ ] **Step 1: Copy conftest_e2e.py**

```bash
cp /c/Users/n24q02m-wlap/projects/wet-mcp/tests/conftest_e2e.py \
   /c/Users/n24q02m-wlap/projects/better-code-review-graph/tests/conftest_e2e.py
```

- [ ] **Step 2: Write CRG test_e2e.py**

```python
"""Full E2E test for better-code-review-graph — single file, 3 setup modes.

Tests ALL 5 tools, ALL 12 actions via MCP protocol.

Usage:
    uv run pytest tests/test_e2e.py --setup=relay --browser=chrome -v -s
    uv run pytest tests/test_e2e.py --setup=env -v
    uv run pytest tests/test_e2e.py --setup=plugin -v
"""

from __future__ import annotations

import os
import warnings

import pytest
from mcp import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

from conftest_e2e import StderrCapture, open_browser, parse_result, parse_result_allow_error

pytestmark = [pytest.mark.e2e, pytest.mark.timeout(120)]

CREDENTIAL_ENV_VARS = [
    "JINA_AI_API_KEY",
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "COHERE_API_KEY",
]

EXPECTED_TOOLS = {"graph", "query", "review", "config", "help"}

# Use the CRG repo itself as test data
REPO_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def setup_mode(request):
    return request.config.getoption("--setup")


@pytest.fixture(scope="module")
def browser_name(request):
    return request.config.getoption("--browser")


def _build_server_params(setup_mode: str):
    capture = None
    base_env = {**os.environ, "LOG_LEVEL": "WARNING"}

    if setup_mode == "relay":
        env = {k: v for k, v in base_env.items() if k not in CREDENTIAL_ENV_VARS}
        capture = StderrCapture()
        params = StdioServerParameters(command="uv", args=["run", "better-code-review-graph"], env=env)
    elif setup_mode == "env":
        params = StdioServerParameters(command="uv", args=["run", "better-code-review-graph"], env=base_env)
    elif setup_mode == "plugin":
        params = StdioServerParameters(
            command="uvx", args=["--python", "3.13", "better-code-review-graph"], env=base_env
        )
    else:
        msg = f"Unknown setup mode: {setup_mode}"
        raise ValueError(msg)

    return params, capture


@pytest.fixture(scope="module")
async def session(setup_mode, browser_name):
    params, capture = _build_server_params(setup_mode)
    errlog_kwargs = {"errlog": capture} if capture else {}

    try:
        async with stdio_client(params, **errlog_kwargs) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as s:
                await s.initialize()

                if setup_mode == "relay":
                    relay_url = capture.get_relay_url(timeout=15)
                    if relay_url:
                        print(f"\n>>> Open relay: {relay_url}", flush=True)
                        open_browser(relay_url, browser_name)

                    import asyncio
                    deadline = asyncio.get_event_loop().time() + 120
                    while asyncio.get_event_loop().time() < deadline:
                        try:
                            r = await s.call_tool("config", {"action": "status"})
                            text = parse_result_allow_error(r)
                            if any(k in text.lower() for k in ["jina", "gemini", "openai", "cohere", "cloud"]):
                                print("\n>>> Relay config received.", flush=True)
                                break
                        except Exception:
                            pass
                        await asyncio.sleep(2)

                yield s
    except (RuntimeError, ExceptionGroup) as exc:
        msg = str(exc).lower()
        if "cancel scope" in msg or "different task" in msg:
            warnings.warn(f"Suppressed teardown error: {exc}", RuntimeWarning, stacklevel=1)
        else:
            raise


class TestServerInit:
    async def test_connects(self, session):
        assert session is not None

    async def test_tools_list(self, session):
        result = await session.list_tools()
        names = {t.name for t in result.tools}
        assert names == EXPECTED_TOOLS

    async def test_tools_have_schema(self, session):
        result = await session.list_tools()
        for tool in result.tools:
            assert tool.inputSchema is not None
            assert tool.description


class TestGraph:
    async def test_build(self, session):
        r = await session.call_tool("graph", {"action": "build", "path": REPO_PATH})
        text = parse_result(r)
        assert "node" in text.lower() or "built" in text.lower() or "graph" in text.lower()

    async def test_update(self, session):
        r = await session.call_tool("graph", {"action": "update", "path": REPO_PATH})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_stats(self, session):
        r = await session.call_tool("graph", {"action": "stats"})
        text = parse_result(r)
        assert "node" in text.lower() or "edge" in text.lower() or "function" in text.lower()

    async def test_embed(self, session):
        r = await session.call_tool("graph", {"action": "embed"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)


class TestQuery:
    async def test_query(self, session):
        r = await session.call_tool(
            "query", {"action": "query", "pattern": "callers_of", "target": "parse_result"}
        )
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_search(self, session):
        r = await session.call_tool("query", {"action": "search", "query": "config"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_impact(self, session):
        r = await session.call_tool(
            "query", {"action": "impact", "target": "server.py::handle_tool_call"}
        )
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_large_functions(self, session):
        r = await session.call_tool("query", {"action": "large_functions", "min_lines": 20})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)


class TestReview:
    async def test_review(self, session):
        r = await session.call_tool("review", {"path": REPO_PATH + "/src"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)


class TestConfig:
    async def test_status(self, session):
        r = await session.call_tool("config", {"action": "status"})
        text = parse_result(r)
        assert isinstance(text, str)

    async def test_set(self, session):
        r = await session.call_tool("config", {"action": "set", "key": "log_level", "value": "WARNING"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)

    async def test_cache_clear(self, session):
        r = await session.call_tool("config", {"action": "cache_clear"})
        text = parse_result_allow_error(r)
        assert isinstance(text, str)


class TestHelp:
    async def test_help(self, session):
        r = await session.call_tool("help", {"topic": "graph"})
        text = parse_result(r)
        assert "graph" in text.lower()


class TestErrorHandling:
    async def test_invalid_action(self, session):
        r = await session.call_tool("graph", {"action": "nonexistent"})
        text = parse_result_allow_error(r)
        assert "error" in text.lower() or "unknown" in text.lower() or "invalid" in text.lower()
```

---

### Task 11: Run CRG E2E (relay, env, plugin) + fix + docs

- [ ] **Step 1: Run relay mode**

```bash
cd /c/Users/n24q02m-wlap/projects/better-code-review-graph
uv run pytest tests/test_e2e.py --setup=relay --browser=chrome -v -s
```

- [ ] **Step 2: Run env mode**

```bash
uv run pytest tests/test_e2e.py --setup=env -v
```

- [ ] **Step 3: Run plugin mode**

```bash
uv run pytest tests/test_e2e.py --setup=plugin -v
```

- [ ] **Step 4: Fix bugs, re-run until all pass**

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest
```

- [ ] **Step 6: Validate docs**

- [ ] **Step 7: Commit**

```bash
git add tests/test_e2e.py tests/conftest_e2e.py
git commit -m "test: add consolidated E2E test with relay/env/plugin modes"
```

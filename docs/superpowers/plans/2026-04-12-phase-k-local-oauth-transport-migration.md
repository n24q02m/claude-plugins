# Phase K — Local OAuth AS + Transport Migration (wet-mcp pilot)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec**: `docs/superpowers/specs/2026-04-10-mcp-core-unified-transport-design.md` (Objectives O14, O15, O16)
**Predecessor**: Phase I2 (mcp-core library complete) + Phase J (7 repos import-renamed to mcp-core)
**Date**: 2026-04-12

**Goal:** Replace stdio + external relay server with local HTTP Streamable transport + self-hosted OAuth 2.1 AS for wet-mcp (pilot). After pilot passes E2E, remaining 4 Python + 1 TS servers follow the same pattern in Phase L.

**Architecture:** Each MCP server becomes an HTTP server on `127.0.0.1:<port>` that serves its own OAuth authorization page (the relay credential form). When an agent connects without a token, it gets 401 + `WWW-Authenticate: Bearer resource_metadata="..."`. The agent auto-opens the authorization page in a browser. User fills the form, server saves credentials to `config.enc`, issues JWT. Agent gets the token and reconnects. No external relay server dependency. Reference implementation: `better-telegram-mcp/src/.../auth_server.py` + `transports/oauth_server.py`.

**Tech Stack:** Python 3.13, FastMCP `http_app(transport="streamable-http")`, Starlette, uvicorn, mcp_core (transport, oauth, lifecycle, storage), starlette Route-based OAuth endpoints.

**Scope limitation:** This plan covers LOCAL MODE ONLY (single-user, `127.0.0.1`). Remote multi-user mode (O16 full) deferred to Phase L2 after all servers run local HTTP.

---

## File Structure

### mcp-core additions (packages/core-py/src/mcp_core/)

| File | Responsibility |
|------|---------------|
| `auth/__init__.py` | Re-exports from auth subpackages |
| `auth/local_oauth_app.py` | Generic Starlette app: OAuth endpoints + credential form HTML + `/mcp` Bearer auth. Reusable across all servers. |
| `auth/credential_form.py` | Render relay-form HTML from `RelayConfigSchema`. Pure function, no side effects. |
| `auth/well_known.py` | `/.well-known/oauth-authorization-server` + `/.well-known/oauth-protected-resource` JSON responses |
| `transport/local_server.py` | High-level entry point: start HTTP server with local OAuth AS, lifecycle lock, auto-open browser. Replaces stdio for local mode. |

### wet-mcp changes (src/wet_mcp/)

| File | Change |
|------|--------|
| `relay_schema.py` | Fix "Search & Extraction: Jina" bug → "SearXNG (local auto-start)" |
| `server.py` | Add `run_http()` alongside current `run()`. Lifespan shared. |
| `__main__.py` | Entry point: detect mode → HTTP (default) or stdio (via `mcp-stdio-proxy`) |
| `credential_state.py` | Keep `resolve_credential_state()` but add `save_credentials()` for OAuth callback |
| `relay_setup.py` | Keep for backward compat (remote relay mode). Local mode bypasses it entirely. |

---

## Pre-flight

- [ ] **Step P.1: Verify current state**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git log --oneline -3
# Expected: latest commits from Phase I2/J

cd C:/Users/n24q02m-wlap/projects/wet-mcp
git log --oneline -3
uv run pytest -q --timeout=30 2>&1 | tail -3
# Expected: 1443+ passed
```

- [ ] **Step P.2: Read reference implementation**

```bash
# better-telegram-mcp already has working local OAuth + HTTP transport
cat C:/Users/n24q02m-wlap/projects/better-telegram-mcp/src/better_telegram_mcp/auth_server.py
cat C:/Users/n24q02m-wlap/projects/better-telegram-mcp/src/better_telegram_mcp/transports/oauth_server.py
```

---

## Task K1: Fix wet-mcp relay_schema.py bug

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/wet-mcp/src/wet_mcp/relay_schema.py:51-54`

- [ ] **Step 1: Fix capabilityInfo**

`relay_schema.py` line 51-54 currently says:
```python
{
    "label": "Search & Extraction",
    "priority": "Jina > SearXNG (local)",
```

Jina does NOT provide web search. SearXNG is the ONLY search provider. Fix:

```python
{
    "label": "Search",
    "priority": "SearXNG (auto-start local)",
    "description": "Web search via SearXNG. Auto-starts locally, no API key needed.",
},
{
    "label": "Extraction",
    "priority": "Built-in (httpx + readability)",
    "description": "Content extraction from URLs. No API key needed.",
},
```

- [ ] **Step 2: Run tests**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
uv run pytest tests/test_relay_setup.py -v
```

- [ ] **Step 3: Commit**

```bash
git add src/wet_mcp/relay_schema.py
git commit -m "fix: correct relay schema capability info for search and extraction"
```

---

## Task K2: mcp-core credential form renderer

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/auth/__init__.py`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/auth/credential_form.py`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/tests/auth/__init__.py`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/tests/auth/test_credential_form.py`

- [ ] **Step 1: Write test for credential form renderer**

```python
# tests/auth/test_credential_form.py
"""Test credential form HTML renderer."""

from mcp_core.auth.credential_form import render_credential_form


def test_render_basic_form():
    schema = {
        "server": "test-server",
        "displayName": "Test Server",
        "description": "Enter your API key.",
        "fields": [
            {
                "key": "API_KEY",
                "label": "API Key",
                "type": "password",
                "placeholder": "sk-...",
                "required": True,
            }
        ],
    }
    html = render_credential_form(schema, submit_url="/oauth/credentials")
    assert "Test Server" in html
    assert "API_KEY" in html
    assert "API Key" in html
    assert "sk-..." in html
    assert 'type="password"' in html
    assert 'action="/oauth/credentials"' in html
    assert "<form" in html


def test_render_optional_fields():
    schema = {
        "server": "test",
        "displayName": "Test",
        "fields": [
            {"key": "KEY1", "label": "Key 1", "type": "password", "required": True},
            {"key": "KEY2", "label": "Key 2", "type": "password", "required": False},
        ],
    }
    html = render_credential_form(schema, submit_url="/submit")
    assert "required" in html  # KEY1 is required
    assert "KEY2" in html


def test_render_capability_info():
    schema = {
        "server": "test",
        "displayName": "Test",
        "fields": [],
        "capabilityInfo": [
            {"label": "Search", "priority": "SearXNG", "description": "Web search."},
        ],
    }
    html = render_credential_form(schema, submit_url="/submit")
    assert "Search" in html
    assert "SearXNG" in html


def test_render_escapes_xss():
    schema = {
        "server": "test",
        "displayName": '<script>alert("xss")</script>',
        "fields": [],
    }
    html = render_credential_form(schema, submit_url="/submit")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
uv run pytest tests/auth/test_credential_form.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_core.auth'`

- [ ] **Step 3: Implement credential_form.py**

```python
# src/mcp_core/auth/credential_form.py
"""Render relay-style credential form HTML from a RelayConfigSchema.

Pure function — takes a schema dict, returns HTML string. No side effects,
no network, no state. Server mounts this at its /authorize endpoint.
"""

from __future__ import annotations

import html as html_module
from typing import Any


def render_credential_form(
    schema: dict[str, Any],
    *,
    submit_url: str,
    page_title: str | None = None,
) -> str:
    """Render an HTML credential form from a RelayConfigSchema.

    Args:
        schema: RelayConfigSchema dict with server, displayName, fields, capabilityInfo.
        submit_url: URL the form POSTs to (e.g., "/oauth/credentials").
        page_title: Override page title (default: schema displayName).
    """
    display_name = html_module.escape(schema.get("displayName", schema.get("server", "MCP Server")))
    description = html_module.escape(schema.get("description", ""))
    title = html_module.escape(page_title or display_name)
    fields = schema.get("fields", [])
    capabilities = schema.get("capabilityInfo", [])

    field_html = []
    for f in fields:
        key = html_module.escape(f["key"])
        label = html_module.escape(f.get("label", key))
        ftype = html_module.escape(f.get("type", "text"))
        placeholder = html_module.escape(f.get("placeholder", ""))
        help_text = html_module.escape(f.get("helpText", ""))
        help_url = html_module.escape(f.get("helpUrl", ""))
        required = f.get("required", False)

        req_attr = "required" if required else ""
        help_link = f'<a href="{help_url}" target="_blank" rel="noopener">Get key</a>' if help_url else ""

        field_html.append(f"""
        <div class="field">
          <label for="{key}">{label} {help_link}</label>
          <input id="{key}" name="{key}" type="{ftype}" placeholder="{placeholder}" {req_attr}>
          {"<p class='help'>" + help_text + "</p>" if help_text else ""}
        </div>""")

    cap_html = []
    for c in capabilities:
        cap_label = html_module.escape(c.get("label", ""))
        cap_priority = html_module.escape(c.get("priority", ""))
        cap_desc = html_module.escape(c.get("description", ""))
        cap_html.append(f"""
        <div class="cap">
          <strong>{cap_label}</strong>: {cap_priority}
          <p class="cap-desc">{cap_desc}</p>
        </div>""")

    safe_submit = html_module.escape(submit_url)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} - Setup</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#0f0f0f;color:#e0e0e0;
  display:flex;justify-content:center;align-items:center;min-height:100vh;padding:1rem}}
.card{{background:#1a1a1a;border:1px solid #333;border-radius:12px;padding:2.5rem;
  max-width:520px;width:100%}}
h1{{font-size:1.5rem;margin-bottom:.5rem;color:#fff}}
.desc{{color:#888;font-size:.875rem;margin-bottom:1.5rem}}
.field{{margin-bottom:1rem}}
label{{display:block;font-size:.875rem;color:#aaa;margin-bottom:.4rem}}
label a{{color:#3b82f6;text-decoration:none;margin-left:.5rem;font-size:.8rem}}
input{{width:100%;padding:.75rem 1rem;background:#111;border:1px solid #444;
  border-radius:8px;color:#fff;font-size:.95rem;outline:none}}
input:focus{{border-color:#3b82f6}}
.help{{font-size:.8rem;color:#666;margin-top:.25rem}}
button{{width:100%;padding:.85rem;background:#3b82f6;color:#fff;border:none;
  border-radius:8px;font-size:1rem;cursor:pointer;font-weight:500;margin-top:1rem}}
button:hover{{background:#2563eb}}
.caps{{margin-top:1.5rem;border-top:1px solid #333;padding-top:1rem}}
.caps h2{{font-size:.95rem;color:#aaa;margin-bottom:.75rem}}
.cap{{margin-bottom:.5rem;font-size:.85rem;color:#ccc}}
.cap-desc{{font-size:.8rem;color:#666;margin-top:.15rem}}
.st{{margin-top:1rem;padding:.75rem;border-radius:8px;font-size:.875rem;display:none}}
.st.error{{display:block;background:#2d1111;border:1px solid #dc2626;color:#f87171}}
.st.success{{display:block;background:#0d2818;border:1px solid #16a34a;color:#4ade80}}
</style>
</head>
<body>
<div class="card">
  <h1>{display_name}</h1>
  {"<p class='desc'>" + description + "</p>" if description else ""}

  <form id="cred-form" method="POST" action="{safe_submit}">
    {"".join(field_html)}
    <button type="submit">Save Configuration</button>
  </form>
  <div id="status" class="st"></div>

  {"<div class='caps'><h2>Capability Priority</h2>" + "".join(cap_html) + "</div>" if cap_html else ""}

  <script>
  document.getElementById('cred-form').addEventListener('submit', async function(e) {{
    e.preventDefault();
    const btn = this.querySelector('button');
    const st = document.getElementById('status');
    btn.disabled = true; btn.textContent = 'Saving...';
    st.className = 'st'; st.style.display = 'none';
    try {{
      const fd = new FormData(this);
      const body = Object.fromEntries(fd.entries());
      const r = await fetch(this.action, {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify(body)
      }});
      const d = await r.json();
      if (d.ok) {{
        st.className = 'st success'; st.textContent = d.message || 'Configuration saved! You can close this tab.';
        st.style.display = 'block';
      }} else {{
        st.className = 'st error'; st.textContent = d.error || 'Failed to save.';
        st.style.display = 'block';
        btn.disabled = false; btn.textContent = 'Save Configuration';
      }}
    }} catch(err) {{
      st.className = 'st error'; st.textContent = 'Network error.';
      st.style.display = 'block';
      btn.disabled = false; btn.textContent = 'Save Configuration';
    }}
  }});
  </script>
</div>
</body>
</html>"""
```

- [ ] **Step 4: Create `auth/__init__.py`**

```python
# src/mcp_core/auth/__init__.py
"""MCP Core authentication module."""

from mcp_core.auth.credential_form import render_credential_form

__all__ = ["render_credential_form"]
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/auth/test_credential_form.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-py/src/mcp_core/auth/ packages/core-py/tests/auth/
git commit -m "feat: add credential form HTML renderer for local OAuth AS"
```

---

## Task K3: mcp-core well-known metadata endpoints

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/auth/well_known.py`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/tests/auth/test_well_known.py`

- [ ] **Step 1: Write test**

```python
# tests/auth/test_well_known.py
"""Test OAuth well-known metadata generators."""

from mcp_core.auth.well_known import (
    authorization_server_metadata,
    protected_resource_metadata,
)


def test_authorization_server_metadata():
    meta = authorization_server_metadata("http://127.0.0.1:9876")
    assert meta["issuer"] == "http://127.0.0.1:9876"
    assert meta["authorization_endpoint"] == "http://127.0.0.1:9876/authorize"
    assert meta["token_endpoint"] == "http://127.0.0.1:9876/token"
    assert "S256" in meta["code_challenge_methods_supported"]
    assert "authorization_code" in meta["grant_types_supported"]


def test_protected_resource_metadata():
    meta = protected_resource_metadata(
        resource="http://127.0.0.1:9876",
        authorization_servers=["http://127.0.0.1:9876"],
    )
    assert meta["resource"] == "http://127.0.0.1:9876"
    assert "http://127.0.0.1:9876" in meta["authorization_servers"]
```

- [ ] **Step 2: Run to verify fail, implement, run to verify pass**

```python
# src/mcp_core/auth/well_known.py
"""OAuth 2.1 well-known metadata generators (RFC 8414 + RFC 9728)."""

from __future__ import annotations


def authorization_server_metadata(issuer_url: str) -> dict:
    """RFC 8414 OAuth Authorization Server Metadata."""
    return {
        "issuer": issuer_url,
        "authorization_endpoint": f"{issuer_url}/authorize",
        "token_endpoint": f"{issuer_url}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
    }


def protected_resource_metadata(
    resource: str,
    authorization_servers: list[str],
) -> dict:
    """RFC 9728 OAuth Protected Resource Metadata."""
    return {
        "resource": resource,
        "authorization_servers": authorization_servers,
        "bearer_methods_supported": ["header"],
    }
```

- [ ] **Step 3: Update auth/__init__.py, commit**

---

## Task K4: mcp-core local OAuth Starlette app

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/auth/local_oauth_app.py`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/tests/auth/test_local_oauth_app.py`

This is the core module. It creates a Starlette app with:
- `GET /authorize` — renders credential form HTML
- `POST /authorize` — receives credentials, saves to config.enc, returns auth code
- `POST /token` — exchanges auth code for JWT access token (PKCE verified)
- `GET /.well-known/oauth-authorization-server` — metadata
- `GET /.well-known/oauth-protected-resource` — resource metadata
- `POST|GET|DELETE /mcp` — MCP Streamable HTTP endpoint (Bearer auth required)

**Reference**: `better-telegram-mcp/src/.../transports/oauth_server.py` (lines 44-287)

- [ ] **Step 1: Write integration test**

Test should verify:
1. GET /authorize returns HTML form
2. POST /authorize with credentials → saves + returns redirect with code
3. POST /token with code + code_verifier → returns JWT
4. GET /mcp without token → 401 with WWW-Authenticate header
5. GET /mcp with valid JWT → proxied to MCP server

Use `starlette.testclient.TestClient` for sync testing.

- [ ] **Step 2: Implement local_oauth_app.py**

Pattern from better-telegram-mcp `oauth_server.py` but generalized:
- Takes `FastMCP` instance + `RelayConfigSchema` + `config_save_callback`
- No Telegram-specific logic
- Uses `mcp_core.auth.credential_form.render_credential_form` for form HTML
- Uses `mcp_core.oauth.jwt_issuer.JWTIssuer` for token signing
- Uses `mcp_core.storage.config_file.write_config` for credential persistence

- [ ] **Step 3: Run tests, commit**

---

## Task K5: mcp-core local server entry point

**Files:**
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/transport/local_server.py`
- Create: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/tests/transport/test_local_server.py`

High-level function:

```python
async def run_local_server(
    mcp: FastMCP,
    *,
    server_name: str,
    relay_schema: dict,
    port: int = 0,  # 0 = auto-find free port
    open_browser: bool = True,
) -> None:
    """Start MCP server with local OAuth AS on 127.0.0.1."""
```

This replaces `mcp.run()` (stdio) for servers that need credentials.

- [ ] **Step 1: Write test, implement, verify, commit**

---

## Task K6: wet-mcp transport migration

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/wet-mcp/src/wet_mcp/server.py`
- Modify: `C:/Users/n24q02m-wlap/projects/wet-mcp/src/wet_mcp/__main__.py`
- Modify: `C:/Users/n24q02m-wlap/projects/wet-mcp/src/wet_mcp/credential_state.py`

- [ ] **Step 1: Add `run_http()` to server.py**

After the existing `mcp = FastMCP(...)` block, add:

```python
async def run_http(port: int = 0) -> None:
    """Run wet-mcp as local HTTP server with OAuth credential flow."""
    from mcp_core.transport.local_server import run_local_server
    from wet_mcp.relay_schema import RELAY_SCHEMA

    await run_local_server(
        mcp,
        server_name="wet-mcp",
        relay_schema=RELAY_SCHEMA,
        port=port,
    )
```

- [ ] **Step 2: Update `__main__.py` entry point**

```python
def main():
    import asyncio
    from wet_mcp.server import run_http
    asyncio.run(run_http())
```

Keep old stdio path behind `--stdio` flag or `MCP_TRANSPORT=stdio` env var for backward compat during transition.

- [ ] **Step 3: Update credential_state.py**

Add `save_credentials(config: dict)` function that writes to config.enc — called by the OAuth form submit handler.

- [ ] **Step 4: Run tests**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
uv run pytest --timeout=30 -q
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add HTTP transport with local OAuth AS, replace stdio default"
```

---

## Task K7: E2E verification (wet-mcp local OAuth)

- [ ] **Step 1: Clean state**

```bash
rm -f ~/.config/mcp/config.enc
# Unset all cloud API key env vars
```

- [ ] **Step 2: Start wet-mcp from source**

```bash
cd C:/Users/n24q02m-wlap/projects/wet-mcp
uv run wet-mcp
```

Expected:
- Server binds to `127.0.0.1:<port>`
- Browser auto-opens to `http://127.0.0.1:<port>/authorize`
- Credential form displays (API keys for Jina, Gemini, OpenAI, Cohere)

- [ ] **Step 3: Fill form and submit**

User enters API keys in form → submit → server saves to config.enc → page shows "Configuration saved!"

- [ ] **Step 4: MCP protocol test**

```python
# Connect via mcp.ClientSession over HTTP (not stdio)
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://127.0.0.1:<port>/mcp", headers={"Authorization": "Bearer <token>"}) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        # Test search, extract, media, help, config, setup
```

- [ ] **Step 5: Verify all tools work with real data**

Test each action: search/search, search/docs, extract/extract, extract/convert, media/discover, help/*, config/status, setup/*.

- [ ] **Step 6: Verify restart persistence**

Stop server → restart → credentials load from config.enc → tools work immediately without re-configuring.

---

## Task K8: GDrive appdata scope migration (wet-mcp)

Per spec §2.6. Deferred to sub-task — can be done independently after K1-K7.

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/wet-mcp/src/wet_mcp/sync.py`
- Modify: OAuth scope from `drive.file` to `drive.appdata`

- [ ] **Step 1: Change OAuth scope in sync.py**
- [ ] **Step 2: Add one-time migration routine (detect old folders, upload to appdata)**
- [ ] **Step 3: Test sync with appdata scope**
- [ ] **Step 4: Commit**

---

## Exit criteria for Phase K

- [ ] mcp-core has `auth/` package with credential form renderer + well-known metadata + local OAuth app
- [ ] wet-mcp runs as HTTP server (not stdio) by default
- [ ] wet-mcp serves its own credential form at `/authorize` (no external relay server)
- [ ] Agent gets 401 → auto-opens browser → user configures → tools work
- [ ] Restart persistence: config.enc survives restart
- [ ] relay_schema.py "Jina search" bug fixed
- [ ] All existing unit tests still pass
- [ ] E2E verified with real API keys (Jina, Gemini, etc.)
- [ ] GDrive sync works with drive.file scope (drive.appdata incompatible with device code flow)

**Next phase**: Phase L — apply same pattern to ALL 7 servers:
- mnemo-mcp: mcp-core Self-hosted AS + GDrive device code (DONE)
- better-code-review-graph: mcp-core Self-hosted AS (DONE)
- better-telegram-mcp: migrate from own http transport to mcp-core Self-hosted AS (relay form with bot token + phone fields)
- better-email-mcp: migrate from own http transport to mcp-core Self-hosted AS (relay form with email credential fields)
- better-notion-mcp: migrate from own http transport to mcp-core Self-hosted AS (local: paste integration token; remote: delegated Notion OAuth)
- better-godot-mcp: HTTP transport (no OAuth, no credentials — Streamable HTTP only)
- E2E test ALL 7 servers: full/real/live, interactive with user, all tools/actions/modes

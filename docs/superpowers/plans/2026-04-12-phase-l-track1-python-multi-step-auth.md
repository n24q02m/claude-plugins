# Phase L Track 1 — Multi-step Auth + Telegram Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend mcp-core Python with multi-step auth (`/otp` endpoint) and integrate into better-telegram-mcp so user mode OTP + 2FA works via the credential form instead of relay messaging.

**Architecture:** Add `/otp` endpoint to `local_oauth_app.py`, extend credential form JS to handle `otp_required`/`password_required`/`error` next_step types, then refactor telegram's `credential_state.py` to use the new callbacks instead of relay-based `_relay_telethon_auth`.

**Tech Stack:** Python 3.13, Starlette, FastMCP, Telethon, mcp-core (local_oauth_app, credential_form)

**Spec:** `docs/superpowers/specs/2026-04-12-phase-l-multi-step-auth-and-core-ts-design.md` Section 2.1, 3.1

---

## File Structure

### mcp-core changes (packages/core-py/src/mcp_core/)

| File | Change | Responsibility |
|------|--------|----------------|
| `auth/local_oauth_app.py` | Modify | Add `/otp` endpoint, `on_step_submitted` callback parameter |
| `auth/credential_form.py` | Modify | Add `otp_required`, `password_required`, `error` handling in form JS |
| `transport/local_server.py` | Modify | Pass `on_step_submitted` through to `create_local_oauth_app` |

### mcp-core tests

| File | Change |
|------|--------|
| `tests/auth/test_local_oauth_app.py` | Modify -- add `/otp` endpoint tests |
| `tests/auth/test_credential_form.py` | Modify -- add multi-step next_step snapshot tests |

### better-telegram-mcp changes

| File | Change | Responsibility |
|------|--------|----------------|
| `src/better_telegram_mcp/credential_state.py` | Modify | Refactor `save_credentials` to return `otp_required`, add `on_step_submitted` |
| `src/better_telegram_mcp/server.py` | Modify | Pass `on_step_submitted` to `run_local_server` |
| `src/better_telegram_mcp/relay_setup.py` | Modify | Remove `_relay_telethon_auth` (replaced by `/otp` flow) |

---

## Pre-flight

- [ ] **Step P.1: Verify mcp-core current state**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git log --oneline -3
cd packages/core-py
uv run pytest -q --timeout=30 2>&1 | tail -3
```

Expected: latest commit `bc8ed03`, tests pass.

- [ ] **Step P.2: Verify better-telegram-mcp current state**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
git log --oneline -3
uv run pytest -q --timeout=30 2>&1 | tail -5
```

Expected: latest commit `b14078d`, tests pass.

---

## Task L1.1: Add `/otp` endpoint to local_oauth_app.py

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/auth/local_oauth_app.py`
- Modify: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/tests/auth/test_local_oauth_app.py`

- [ ] **Step 1: Write test for `/otp` endpoint**

Add to `tests/auth/test_local_oauth_app.py`:

```python
def test_otp_endpoint_completes_setup(client_with_otp):
    """POST /otp with valid step data should complete setup."""
    client, saved = client_with_otp

    # First: submit credentials that trigger OTP
    params = _authorize_params()
    client.get("/authorize", params=params)
    nonce = _extract_nonce(client)
    resp = client.post(f"/authorize?nonce={nonce}", json={"TELEGRAM_PHONE": "+1234567890"})
    data = resp.json()
    assert data["ok"] is True
    assert data["next_step"]["type"] == "otp_required"

    # Then: submit OTP
    resp = client.post("/otp", json={"otp_code": "12345"})
    data = resp.json()
    assert data["ok"] is True
    assert "next_step" not in data  # complete


def test_otp_endpoint_chains_to_password(client_with_2fa):
    """POST /otp should chain to password_required when callback says so."""
    client, saved = client_with_2fa

    params = _authorize_params()
    client.get("/authorize", params=params)
    nonce = _extract_nonce(client)
    client.post(f"/authorize?nonce={nonce}", json={"TELEGRAM_PHONE": "+1234567890"})

    # OTP step
    resp = client.post("/otp", json={"otp_code": "12345"})
    data = resp.json()
    assert data["ok"] is True
    assert data["next_step"]["type"] == "password_required"

    # Password step
    resp = client.post("/otp", json={"password": "secret"})
    data = resp.json()
    assert data["ok"] is True
    assert "next_step" not in data


def test_otp_endpoint_returns_error(client_with_otp_error):
    """POST /otp should return error when callback returns error."""
    client, saved = client_with_otp_error

    params = _authorize_params()
    client.get("/authorize", params=params)
    nonce = _extract_nonce(client)
    client.post(f"/authorize?nonce={nonce}", json={"TELEGRAM_PHONE": "+1234567890"})

    resp = client.post("/otp", json={"otp_code": "wrong"})
    data = resp.json()
    assert data["ok"] is False
    assert "Invalid" in data["error"]


def test_otp_endpoint_without_prior_authorize(client_with_otp):
    """POST /otp without prior credential submission should fail."""
    client, _ = client_with_otp
    resp = client.post("/otp", json={"otp_code": "12345"})
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"] == "invalid_request"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
uv run pytest tests/auth/test_local_oauth_app.py -v -k "otp"
```

Expected: FAIL -- no `/otp` route, no fixtures.

- [ ] **Step 3: Implement `/otp` endpoint in local_oauth_app.py**

Modify `create_local_oauth_app` in `local_oauth_app.py`:

1. Add `on_step_submitted` parameter to function signature.

2. Add module-level state for pending OTP session inside the closure:
```python
    _pending_step: dict[str, Any] = {}
```

3. In `authorize_post`, after `on_credentials_saved` returns `next_step`, if `next_step.type` is `otp_required` or `password_required`, mark step active:
```python
        if next_step and next_step.get("type") in ("otp_required", "password_required"):
            _pending_step["active"] = True
            _pending_step["created_at"] = time.monotonic()
            _pending_step["attempts"] = 0
```

4. Add `/otp` handler with:
   - Check `_pending_step["active"]` -- 400 if not active
   - Check timeout (300s) -- 400 if expired
   - Check attempt limit (5) -- 400 if exceeded
   - Parse JSON body
   - Call `on_step_submitted(step_data)` callback
   - If returns `None` -- clear pending, return `{"ok": true}`
   - If returns `{"type": "error", ...}` -- return `{"ok": false, "error": ...}` (don't clear pending, allow retry)
   - If returns next step -- return `{"ok": true, "next_step": ...}`

5. Add route `Route("/otp", otp_handler, methods=["POST"])` to routes list.

- [ ] **Step 4: Add test fixtures**

Add fixtures `client_with_otp`, `client_with_2fa`, `client_with_otp_error` and helpers `_authorize_params`, `_extract_nonce` to the test file. Each fixture creates a `TestClient` with appropriate `on_credentials_saved` and `on_step_submitted` callbacks that simulate the OTP flow.

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
uv run pytest tests/auth/test_local_oauth_app.py -v -k "otp"
```

Expected: 4 tests PASS.

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest -q --timeout=30
```

Expected: all existing tests still pass.

- [ ] **Step 7: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-py/src/mcp_core/auth/local_oauth_app.py packages/core-py/tests/auth/test_local_oauth_app.py
git commit -m "feat: add /otp endpoint for multi-step auth in local OAuth AS"
```

---

## Task L1.2: Extend credential form JS for multi-step input

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/auth/credential_form.py`
- Modify: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/tests/auth/test_credential_form.py`

- [ ] **Step 1: Write test for multi-step form rendering**

Add to `tests/auth/test_credential_form.py`:

```python
def test_render_form_contains_otp_handler():
    """Form JS should handle next_step type otp_required."""
    schema = {"server": "test", "displayName": "Test", "fields": []}
    html = render_credential_form(schema, submit_url="/authorize?nonce=abc")
    assert "otp_required" in html
    assert "password_required" in html
    assert "/otp" in html


def test_render_form_contains_error_retry():
    """Form JS should allow retry on error without clearing input."""
    schema = {"server": "test", "displayName": "Test", "fields": []}
    html = render_credential_form(schema, submit_url="/authorize?nonce=abc")
    # Verify the JS has error handling that re-enables the button
    assert "Verify" in html
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
uv run pytest tests/auth/test_credential_form.py -v -k "otp_handler or error_retry"
```

Expected: FAIL -- form JS doesn't contain `otp_required` handling yet.

- [ ] **Step 3: Extend form JS in credential_form.py**

In the `<script>` section of `render_credential_form`, add handling for `otp_required` and `password_required` next_step types after the existing `oauth_device_code` and `info` handlers.

The new JS code should:
1. Hide the original form fields when `otp_required`/`password_required` is received
2. Create a new input field (text for OTP, password for 2FA) with a "Verify" button
3. On submit, POST to `/otp` (derived from submit URL by replacing `/authorize...` with `/otp`)
4. Handle chained responses: if `/otp` returns another `next_step`, update the input field in place
5. On error response, show error message and re-enable input for retry
6. On success (no `next_step`), show "Setup complete!"
7. Support Enter key to submit

**Security note**: Use DOM creation methods (`document.createElement`) for dynamic elements instead of string concatenation with user content. The step text from server responses should be set via `textContent`, not inserted as HTML.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
uv run pytest tests/auth/test_credential_form.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Run full test suite**

```bash
uv run pytest -q --timeout=30
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-py/src/mcp_core/auth/credential_form.py packages/core-py/tests/auth/test_credential_form.py
git commit -m "feat: extend credential form JS with multi-step OTP and password input"
```

---

## Task L1.3: Pass `on_step_submitted` through local_server.py

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/transport/local_server.py:101-146` (build_local_app)
- Modify: `C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py/src/mcp_core/transport/local_server.py:179-232` (run_local_server)

- [ ] **Step 1: Add `on_step_submitted` to `build_local_app`**

Add parameter `on_step_submitted: Callable[[dict[str, str]], dict | None] | None = None` to the function signature. Pass it to `create_local_oauth_app()` call.

- [ ] **Step 2: Add `on_step_submitted` to `run_local_server`**

Add same parameter to `run_local_server` signature. Pass it to `build_local_app()` call. Update docstring.

- [ ] **Step 3: Run full test suite**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core/packages/core-py
uv run pytest -q --timeout=30
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/n24q02m-wlap/projects/mcp-core
git add packages/core-py/src/mcp_core/transport/local_server.py
git commit -m "feat: pass on_step_submitted callback through local server entry point"
```

---

## Task L1.4: Refactor telegram credential_state.py for multi-step auth

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/better-telegram-mcp/src/better_telegram_mcp/credential_state.py`

- [ ] **Step 1: Add module-level state for multi-step flow**

Add after existing globals:

```python
# Multi-step auth state (module-level, single-user local mode)
_step_backend: object | None = None  # UserBackend instance during OTP flow
_step_phone: str = ""
_step_otp_code: str | None = None
```

- [ ] **Step 2: Add async helper for Telethon connect + send_code**

```python
async def _connect_and_send_code(backend: object, phone: str) -> None:
    """Connect Telethon backend and send OTP code."""
    await backend.connect()
    await backend.send_code(phone)
```

- [ ] **Step 3: Refactor `save_credentials` user mode branch**

Replace the user mode branch (lines 338-351) to:
1. Create `UserBackend` from config
2. Call `_connect_and_send_code` to start Telethon and send OTP
3. Store backend reference in `_step_backend` for later use by `on_step_submitted`
4. Return `{"type": "otp_required", "text": "Enter the OTP code sent to your Telegram app", "field": "otp_code", "input_type": "text"}`
5. On error, return `{"type": "error", "text": "Failed to send OTP: ..."}`

- [ ] **Step 4: Add `on_step_submitted` function**

Implement with two branches:
1. `"otp_code"` in step_data: call `_step_backend.sign_in(phone, code)`. On success return `None`. On 2FA needed, return `{"type": "password_required", ...}`. On other error, return `{"type": "error", ...}`.
2. `"password"` in step_data: call `_step_backend.sign_in(phone, code, password=password)`. On success return `None`. On error, return `{"type": "error", ...}`.

Add `_finalize_auth()` helper that: sets `_state = CONFIGURED`, disconnects `_step_backend`, clears step state, calls `_on_configured_callback`.

Add `_needs_2fa_password(error_msg)` helper with regex check.

- [ ] **Step 5: Run telegram tests**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
uv run pytest -q --timeout=30
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/better_telegram_mcp/credential_state.py
git commit -m "feat: refactor credential_state for multi-step OTP via /otp endpoint"
```

---

## Task L1.5: Wire `on_step_submitted` in telegram server.py

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/better-telegram-mcp/src/better_telegram_mcp/server.py:548-561`

- [ ] **Step 1: Update `run_http` to pass `on_step_submitted`**

Import `on_step_submitted` from `.credential_state` and pass to `run_local_server`:

```python
async def run_http(port: int = 0) -> None:
    """Run as HTTP server with local OAuth 2.1 AS via mcp-core."""
    from mcp_core.transport.local_server import run_local_server

    from .credential_state import on_step_submitted, save_credentials
    from .relay_schema import RELAY_SCHEMA

    await run_local_server(
        mcp,
        server_name="better-telegram-mcp",
        relay_schema=RELAY_SCHEMA,
        port=port,
        on_credentials_saved=save_credentials,
        on_step_submitted=on_step_submitted,
    )
```

- [ ] **Step 2: Run tests**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
uv run pytest -q --timeout=30
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add src/better_telegram_mcp/server.py
git commit -m "feat: wire on_step_submitted callback for multi-step OTP auth"
```

---

## Task L1.6: Clean up relay_setup.py (remove relay OTP flow)

**Files:**
- Modify: `C:/Users/n24q02m-wlap/projects/better-telegram-mcp/src/better_telegram_mcp/relay_setup.py`
- Modify: `C:/Users/n24q02m-wlap/projects/better-telegram-mcp/src/better_telegram_mcp/credential_state.py`

- [ ] **Step 1: Remove `_relay_telethon_auth` from relay_setup.py**

Delete the `_relay_telethon_auth` function (lines ~96-229). Keep `_ERROR_SIMPLIFICATIONS` list and `_sanitize_error` function (still used by credential_state.py).

- [ ] **Step 2: Remove `_handle_user_mode_auth` from credential_state.py**

Delete `_handle_user_mode_auth` function (lines 261-308) -- replaced by `on_step_submitted`. Also remove any references to it in `_poll_relay_background`.

- [ ] **Step 3: Run tests**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
uv run pytest -q --timeout=30
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add src/better_telegram_mcp/relay_setup.py src/better_telegram_mcp/credential_state.py
git commit -m "fix: remove relay-based OTP flow replaced by /otp endpoint"
```

---

## Task L1.7: E2E verification (telegram bot + user mode)

- [ ] **Step 1: Clean state**

```bash
rm -f ~/.config/mcp/config.enc
```

Unset `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PHONE` env vars.

- [ ] **Step 2: Start better-telegram-mcp from source**

```bash
cd C:/Users/n24q02m-wlap/projects/better-telegram-mcp
uv run better-telegram-mcp
```

Expected: server starts on `127.0.0.1:<port>`.

- [ ] **Step 3: Test bot mode**

Open authorize URL in browser with proper PKCE params. Enter bot token, submit. Expected: "Connected successfully" immediately. Verify MCP tools work (help, config/status).

- [ ] **Step 4: Clean state and test user mode**

Delete config.enc, restart server. Open authorize URL. Enter phone number only (leave bot token empty). Submit.

Expected flow:
1. Form shows "Enter the OTP code sent to your Telegram app" with text input
2. Enter OTP from Telegram app
3. If 2FA: form shows "Enter your 2FA password" with password input
4. After verification: "Setup complete!"

Verify: MCP tools work (message/send, chat/list).

- [ ] **Step 5: Restart persistence**

Stop server, restart. Credentials load from config.enc. Tools work immediately without re-auth.

---

## Exit criteria for Track 1

- [ ] mcp-core: `/otp` endpoint with timeout (300s) and rate limit (5 attempts)
- [ ] mcp-core: credential form JS handles `otp_required`, `password_required`, `error`
- [ ] mcp-core: `on_step_submitted` passed through `run_local_server`
- [ ] telegram: bot mode unchanged (token -> complete)
- [ ] telegram: user mode OTP via `/otp` endpoint (not relay messaging)
- [ ] telegram: 2FA password chaining
- [ ] telegram: old relay OTP flow removed
- [ ] All unit tests pass in both repos
- [ ] E2E: bot mode + user mode with real credentials

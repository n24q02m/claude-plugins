# Phase G7 — credential_state inventory for Phase J deletion list

Date: 2026-04-11
Executed by: Claude Code session (Phase G7 subagent)
Spec: `specs/2026-04-10-mcp-core-unified-transport-design.md` §2.7(b)
Plan: `plans/2026-04-11-phase-g-unblock.md`

## Context

Phase 3 spec §2.7(b) mandates deletion of `credential_state.py` / `credential-state.ts` files + inline `AWAITING_SETUP` gates in 6 credential repos. OAuth 2.1 transport middleware in `mcp-core` will handle 401 responses instead. This evidence file captures the exact Phase J deletion target list.

## Files to delete (from G7.1)

### wet-mcp

```
wet-mcp/src/wet_mcp/credential_state.py
wet-mcp/tests/test_credential_state.py
```

### mnemo-mcp

```
mnemo-mcp/src/mnemo_mcp/credential_state.py
mnemo-mcp/tests/test_credential_state.py
```

### better-code-review-graph

```
better-code-review-graph/src/better_code_review_graph/credential_state.py
better-code-review-graph/tests/test_credential_state.py
```

### better-telegram-mcp

```
better-telegram-mcp/src/better_telegram_mcp/credential_state.py
better-telegram-mcp/tests/test_credential_state.py
```

### better-email-mcp

```
better-email-mcp/src/credential-state.ts
better-email-mcp/src/credential-state.test.ts
```

### better-notion-mcp

```
better-notion-mcp/src/credential-state.ts
```

(no co-located `credential-state.test.ts` — coverage provided via `init-server.test.ts`, `transports/stdio.test.ts`, `tools/composite/setup.test.ts` mocks)

## File count summary

- Total files to delete: **11** (10 impl/test pairs + 1 standalone notion impl)
- Python repos: 4 impl + 4 test = 8
- TypeScript repos: 2 impl + 1 test = 3

## AWAITING_SETUP inline gate sites (from G7.2 + G7.3)

### Python repos — server.py grep output

#### wet-mcp/src/wet_mcp/server.py

```
58:    When state is AWAITING_SETUP: BLOCK the tool — return error with setup instructions.
62:    from wet_mcp.credential_state import CredentialState, get_setup_url, get_state
65:    if state == CredentialState.AWAITING_SETUP:
70:                "state": "awaiting_setup",
146:    from wet_mcp.credential_state import resolve_credential_state
148:    resolve_credential_state()
253:    - AWAITING_SETUP: skip init entirely (tools are blocked anyway)
258:    from wet_mcp.credential_state import CredentialState, get_state
263:    if cred_state == CredentialState.AWAITING_SETUP:
325:    - AWAITING_SETUP: skip init entirely (tools are blocked anyway)
329:    from wet_mcp.credential_state import CredentialState, get_state
333:    if cred_state == CredentialState.AWAITING_SETUP:
1315:            from wet_mcp.credential_state import trigger_relay_setup
1339:            from wet_mcp import credential_state as _cs
1354:            from wet_mcp.credential_state import trigger_relay_setup
1364:            from wet_mcp.credential_state import CredentialState, set_state
1376:            from wet_mcp.credential_state import reset_state
1387:            from wet_mcp.credential_state import (
1389:                resolve_credential_state,
1391:            from wet_mcp.credential_state import (
1395:            resolve_credential_state()
```

#### mnemo-mcp/src/mnemo_mcp/server.py

```
40:    AWAITING_SETUP: skip (FTS5-only mode until user configures credentials).
47:    from mnemo_mcp.credential_state import CredentialState, get_state
52:    if cred_state == CredentialState.AWAITING_SETUP:
126:    AWAITING_SETUP: skip (search works without reranking).
130:    from mnemo_mcp.credential_state import CredentialState, get_state
140:    if cred_state == CredentialState.AWAITING_SETUP:
185:        from mnemo_mcp.credential_state import resolve_credential_state
187:        resolve_credential_state()
282:    """If in awaiting_setup, trigger lazy relay and add hint to response."""
283:    from mnemo_mcp.credential_state import (
289:    if get_state() == CredentialState.AWAITING_SETUP:
1001:            from mnemo_mcp.credential_state import get_setup_url, get_state
1022:            from mnemo_mcp.credential_state import (
1053:            from mnemo_mcp.credential_state import CredentialState, set_state
1065:            from mnemo_mcp.credential_state import reset_state
1076:            from mnemo_mcp.credential_state import (
1079:                resolve_credential_state,
1082:            resolve_credential_state()
1103:            from mnemo_mcp.credential_state import trigger_relay_setup
```

#### better-code-review-graph/src/better_code_review_graph/server.py

```
39:    """If in awaiting_setup, add hint about cloud setup to response."""
40:    from .credential_state import CredentialState, get_setup_url, get_state
42:    if get_state() == CredentialState.AWAITING_SETUP:
504:    - reset: Clear credentials and reset to awaiting_setup
509:            from . import credential_state as _cs
523:            from .credential_state import (
555:            from .credential_state import CredentialState, set_state
567:            from .credential_state import reset_state
578:            from .credential_state import (
581:            from .credential_state import (
582:                resolve_credential_state,
585:            resolve_credential_state()
698:    from .credential_state import resolve_credential_state
700:    resolve_credential_state()
```

#### better-telegram-mcp/src/better_telegram_mcp/server.py

```
93:        from .credential_state import resolve_credential_state
95:        state = resolve_credential_state()
119:        from .credential_state import set_on_configured
414:            from .credential_state import get_setup_url, get_state
432:            from .credential_state import (
459:            from .credential_state import reset_state
470:            from .credential_state import (
473:                resolve_credential_state,
476:            resolve_credential_state()
```

### TypeScript repos — src/*.ts + tools + transports grep output

#### better-email-mcp

```
src/credential-state.ts:2: * Non-blocking credential state management for better-email-mcp.
src/credential-state.ts:4: * State machine: awaiting_setup -> setup_in_progress -> configured
src/credential-state.ts:5: * Reset: configured -> awaiting_setup (via explicit reset)
src/credential-state.ts:8: * When state is AWAITING_SETUP, tools return a clear error with setup URL.
src/credential-state.ts:23:export type CredentialState = 'awaiting_setup' | 'setup_in_progress' | 'configured'
src/credential-state.ts:25:let state: CredentialState = 'awaiting_setup'
src/credential-state.ts:43: * 4. NOTHING -- state = awaiting_setup (server starts fast, relay triggered lazily)
src/credential-state.ts:91:console.error('No credentials found -- server starting in awaiting_setup mode')
src/credential-state.ts:92:state = 'awaiting_setup'
src/credential-state.ts:105:if (!options?.force && state !== 'awaiting_setup') {
src/credential-state.ts:133:state = 'awaiting_setup'
src/credential-state.ts:167:state = 'awaiting_setup'
src/credential-state.ts:263:/** Reset to awaiting_setup (used by setup reset action). */
src/credential-state.ts:265:state = 'awaiting_setup'
src/credential-state.test.ts:49:describe('credential-state', () => {
src/credential-state.test.ts:50:let mod: typeof import('./credential-state.js')
src/credential-state.test.ts:58:mod = await import('./credential-state.js')
src/credential-state.test.ts:67:it('returns awaiting_setup by default', () => {
src/credential-state.test.ts:68:expect(mod.getState()).toBe('awaiting_setup')
src/credential-state.test.ts:118:it('returns awaiting_setup when nothing found', async () => {
src/init-server.test.ts:5:import { resolveCredentialState } from './credential-state.js'
src/init-server.test.ts:16:vi.mock('./credential-state.js', () => ({
src/init-server.test.ts:219:it('starts server with empty accounts when resolveCredentialState returns awaiting_setup', async () => {
src/init-server.test.ts:221:vi.mocked(resolveCredentialState).mockResolvedValue('awaiting_setup')
src/init-server.ts:16:import { resolveCredentialState } from './credential-state.js'
src/tools/registry.ts:5: * Credential-aware: when state is 'awaiting_setup', tools return setup
src/tools/registry.ts:20:import { getSetupUrl, getState, triggerRelaySetup } from '../credential-state.js'
src/tools/registry.ts:349:if (credState === 'awaiting_setup') {
src/tools/registry-call-tool.test.ts:11:// Mock credential state to return 'configured' so tools execute normally
src/tools/registry-call-tool.test.ts:12:vi.mock('../credential-state.js', () => ({
src/tools/registry-error-handler.test.ts:12:// Mock credential state to return 'configured' so tools execute normally
src/tools/registry-error-handler.test.ts:13:vi.mock('../credential-state.js', () => ({
src/tools/registry.logic.test.ts:15:// Mock credential state to return 'configured' so tools execute normally
src/tools/registry.logic.test.ts:16:vi.mock('../credential-state.js', () => ({
src/tools/composite/setup.test.ts:5:vi.mock('../../credential-state.js', () => ({
src/tools/composite/setup.test.ts:13:import { getSetupUrl, getState, resetState, resolveCredentialState, triggerRelaySetup } from '../../credential-state.js'
```

#### better-notion-mcp

```
src/credential-state.ts:2: * Non-blocking credential state management for better-notion-mcp.
src/credential-state.ts:4: * State machine: awaiting_setup -> setup_in_progress -> configured
src/credential-state.ts:5: * Reset: configured -> awaiting_setup (via reset)
src/credential-state.ts:8: * When state is AWAITING_SETUP, token-requiring tools return setup instructions with relay URL.
src/credential-state.ts:23:export type CredentialState = 'awaiting_setup' | 'setup_in_progress' | 'configured'
src/credential-state.ts:26:let _state: CredentialState = 'awaiting_setup'
src/credential-state.ts:49: * 3. NOTHING -- awaiting_setup (server starts fast, relay triggered lazily)
src/credential-state.ts:77:console.error('No Notion token found -- server starting in awaiting_setup mode')
src/credential-state.ts:78:_state = 'awaiting_setup'
src/credential-state.ts:89:if (_state !== 'awaiting_setup') {
src/credential-state.ts:105:_state = 'awaiting_setup'
src/credential-state.ts:127:console.error(`Relay setup failed: ${err}. Server continues in awaiting_setup.`)
src/credential-state.ts:128:_state = 'awaiting_setup'
src/credential-state.ts:169:_state = 'awaiting_setup'
src/credential-state.ts:198:_state = 'awaiting_setup'
src/init-server.test.ts:33:vi.mock('./credential-state.js', () => ({
src/init-server.test.ts:34:resolveCredentialState: vi.fn().mockResolvedValue('awaiting_setup')
src/init-server.test.ts:36:getState: vi.fn().mockReturnValue('awaiting_setup')
src/init-server.test.ts:67:const { resolveCredentialState, getNotionToken } = await import('./credential-state.js')
src/transports/stdio.ts:16:} from '../credential-state.js'
src/transports/stdio.ts:46:if (currentState === 'awaiting_setup') {
src/transports/stdio.test.ts:16:vi.mock('../credential-state.js', () => ({
src/transports/stdio.test.ts:127:vi.mocked(resolveCredentialState).mockResolvedValue('awaiting_setup')
src/transports/stdio.test.ts:129:vi.mocked(getState).mockReturnValue('awaiting_setup')
src/transports/stdio.test.ts:149:vi.mocked(resolveCredentialState).mockResolvedValue('awaiting_setup')
src/tools/registry.ts:17:import { getSetupUrl, getState, triggerRelaySetup } from '../credential-state.js'
src/tools/registry.ts:469:if (credState === 'awaiting_setup') {
src/tools/composite/setup.ts:3: * Manage credential state, relay setup, and configuration lifecycle.
src/tools/composite/setup.ts:14:} from '../../credential-state.js'
```

## Inline gate site count summary (server.py + transports + tools/registry)

- wet-mcp server.py: ~21 lines
- mnemo-mcp server.py: ~22 lines
- better-code-review-graph server.py: ~14 lines
- better-telegram-mcp server.py: ~9 lines
- better-email-mcp src/init-server.ts + tools/registry.ts: ~5 production lines (excluding test mocks)
- better-notion-mcp src/init-server.ts (none in init), transports/stdio.ts, tools/registry.ts, tools/composite/setup.ts: ~6 production lines

Total production-code AWAITING_SETUP/credential_state references to remove: **~77 lines** across server entrypoints + transport handlers + tool registries (excluding test fixtures, which get deleted alongside their imports).

## Replacement plan (from spec §2.2 + §2.7(b))

- Delete `credential_state.py` + `test_credential_state.py` in all 6 repos (Phase J per-repo task)
- Remove AWAITING_SETUP blocks in `server.py` / `init-server.ts` / `transports/stdio.ts` / `tools/registry.ts` / `tools/composite/setup.ts`
- Install `mcp_core.auth.middleware` transport-level middleware in `mcp-core`
- Add `Depends(get_session_creds)` to FastMCP tool handlers (Python) or similar injection pattern (TS)
- Tool code assumes credentials present at runtime — middleware handles 401
- Per-repo `setup` tool (`composite/setup.ts`, `tools/config_tool.py`) becomes obsolete: relay flow handled by mcp-core
- Test mocks like `vi.mock('./credential-state.js', ...)` get removed alongside file deletion

## Verification after Phase J

Should return 0 results across all 6 repos:

```bash
grep -rln "AWAITING_SETUP\|credential_state" wet-mcp/src mnemo-mcp/src better-code-review-graph/src better-telegram-mcp/src
grep -rln "AWAITING_SETUP\|credential-state" better-email-mcp/src better-notion-mcp/src
```

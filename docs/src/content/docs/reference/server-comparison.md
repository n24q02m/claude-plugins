---
title: Server comparison
description: Side-by-side comparison of the 7 active servers in the stack, the hull foundation library, and the two archived entries kept for reference.
---

| Server | Tools | Default transport | Multi-user | Docker | Language | License |
|---|---:|---|:-:|:-:|---|---|
| `hull` | — | (foundation lib) | — | — | Python + TypeScript | Apache-2.0 |
| `wet` | 4 + 2 | `http` | yes | GHCR | Python | Apache-2.0 |
| `mnemo` | 5 + 2 | `http` | yes | GHCR | Python | Apache-2.0 |
| `crg` | 5 + 2 | `stdio` | no | GHCR | Python | Apache-2.0 |
| `imagine-mcp` † | 4 + 2 | (archived) | — | GHCR | Python | Apache-2.0 |
| `telegram` | 6 + 2 | `stdio` (+ `http`) | yes | GHCR | Python | Apache-2.0 |
| `notion` | 7 + 2 | `stdio` (+ `http`) | yes | GHCR | TypeScript | Apache-2.0 |
| `email` | 6 + 2 | `stdio` (+ `http`) | no (single-user token) | GHCR | TypeScript | Apache-2.0 |
| `better-godot-mcp` † | 19 + 2 | (archived) | — | GHCR | TypeScript | Apache-2.0 |
| `workspace` | 11 + 2 | `stdio` (+ `http`) | yes | GHCR | TypeScript | Apache-2.0 |

(† archived — docs kept for reference, project no longer maintained.)

(N + 2 = N domain tools plus the universal `help` and `config` tools — see [tool layout standard](/reference/tool-layout-standard/).)

## At a glance

- **wet and mnemo are HTTP-only** — one local process holds the index and models and serves every client on the machine.
- **crg is stdio-only** — it runs as a child of the client (or from the `crg` CLI).
- **telegram, notion, email and workspace default to `stdio`** — HTTP is an opt-in, self-hosted transport with its own auth mode (`no-auth` on loopback, `token`, or `multi`). See the [mode matrix](/reference/mode-matrix/).
- **email HTTP is single-user** — one shared token, no per-user credential store.
- **workspace brings your own Google OAuth client** — the first run consents through a loopback redirect. Its HTTP mode is self-host only; there is no hosted instance.
- **No server has a hosted endpoint** — everything runs on your machine or your own host.
- **hull is not a server** — it's the shared library every active server consumes (HTTP transport, token auth, encrypted credential storage, CLI built-ins). It replaces the archived `mcp-core`.

## Which to install first?

For most users:

- **wet** — search the web. Useful in any agent context.
- **mnemo** — give the agent a long-term memory. Pairs with wet for "what did we discuss last week?" queries.
- **crg** — for code-aware workflows; provides token-efficient code-review context in agent calls.

For specific workflows:

- Coding in unfamiliar repo → `crg`
- Drafting docs/blog → `notion`
- Telegram bot work → `telegram`
- Email triage → `email`
- Google Docs / Drive / Calendar / Gmail → `workspace`

## Versioning

Each server cuts independent releases (`vMAJOR.MINOR.PATCH`). Every active server pins a compatible `hull` range (PyPI `n24q02m-hull`, npm `@n24q02m/hull`), so a breaking `hull` release is adopted by each server in its own release. See each server's CHANGELOG.

`workspace` is still pre-1.0 (npm `@n24q02m/workspace` currently `0.6.0`, with a `beta` dist-tag alongside `latest`), so expect breaking changes before 1.0.

## License

Every repo in the stack is **Apache-2.0**. Several started out MIT and keep the original terms alongside in a `LICENSE-MIT` file, as the MIT license requires; `LICENSE` is the one that governs. `workspace` has been Apache-2.0 from the start, because it vendors Apache-2.0 code from [gemini-cli-extensions/workspace](https://github.com/gemini-cli-extensions/workspace) and keeps that license for the whole repo.

Forks and self-host welcome — no license fees, no telemetry phoning home.

## See also

- [Mode matrix](/reference/mode-matrix/)
- [Tool layout standard](/reference/tool-layout-standard/)
- [Multi-user pattern](/reference/multi-user-pattern/)

---
title: Credential setup
description: How credentials reach each server — environment, CLI, the config tool, and config.toml model cells.
---

Every server runs on a machine you control, and credentials stay on that machine. There is no browser form, no redirect URL and no hosted endpoint involved. Which route applies depends on the server and on the [transport and auth mode](/reference/mode-matrix/) you run.

## Where credentials come from

| Route | Used by | How |
|---|---|---|
| Environment variables | every `stdio` server | Put them in the `env` block of the client's MCP config, or export them before starting the server. |
| `<server> auth` CLI | `telegram`, `notion`, `email`, `workspace` | Run on the host, for example `telegram auth` or `notion auth --user <namespace>`. Credentials are encrypted into the server's data directory. |
| The `config` tool | HTTP `multi` users of `notion` | The user stores their own credentials from the client by calling the `config` tool. |
| `~/.<server>/config.toml` | `wet`, `mnemo`, `crg`, `telegram` | Static settings, including model cells for LLM, embedding and rerank providers. |

When a `stdio` server starts without the credentials it needs, it prints a one-line hint naming the command to run (for example `telegram auth`) on stderr and exits non-zero. Nothing is asked over the MCP channel.

## Model cells (wet, mnemo, crg)

Embedding, reranking and chat models are configured as cells in `~/.<server>/config.toml`:

```toml
[models.embed]
base_url = "https://openrouter.ai/api/v1"
model    = "<embedding-model-id>"
api_key  = ""          # prefer the environment variable below

[models.chat]
base_url = "https://openrouter.ai/api/v1"
model    = "<chat-model-id>"
```

- An environment variable `HULL_<TASK>_API_KEY` (for example `HULL_EMBED_API_KEY`) overrides the key in the file.
- `OPENROUTER_API_KEY` serves the pre-wired default cells.
- With an empty `embed` or `rerank` cell the server uses local ONNX models through [FastRetrieval](/reference/fastretrieval/); no key is needed.
- With no `chat` key, features that need an LLM are switched off instead of failing.
- `crg` also reads `EMBEDDING_MODELS` (comma-separated, empty means local ONNX) and the opt-in `LOCAL_RERANK_MODEL`.

## Search providers (wet)

`SEARCH_BACKENDS` is a comma-separated list chosen from `searxng`, `tavily`, `brave`, `exa`, `kagi`, `openrouter`, `firecrawl`, `duckduckgo` and `startpage`. Providers that need a key read it from their own environment variable; keyless providers (`duckduckgo`, `startpage`) work out of the box.

## Google Workspace

`workspace` never accepts pasted Google credentials. Consent happens on Google's own screen and the resulting token is stored encrypted on the host:

- `stdio`: `workspace auth` opens the consent flow with the Desktop OAuth client.
- `http`: the operator runs `workspace auth --user <namespace>` on the host for each namespace; the Web OAuth client is used. `CREDENTIAL_SECRET` must be set. This HTTP consent path has not yet been verified end to end.

## Rules of thumb

- Keep secrets in environment variables or your secret manager, not in `config.toml` committed to a repository.
- Never put a token in a URL query string.
- Stored credentials are encrypted with a machine key; copying a data directory to another machine does not carry them over — run the auth command there instead.

## Read more

- [Modes overview](/get-started/modes-overview/)
- [Mode matrix](/reference/mode-matrix/)
- [Multi-user pattern](/reference/multi-user-pattern/)

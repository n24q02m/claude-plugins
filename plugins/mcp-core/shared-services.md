---
title: Shared services
description: Common services exposed by mcp-core to consumer servers.
---

## README

# Shared Embedding Daemon (opt-in)

`docker-compose.yml` in this directory runs the shared
`mcp-embedding-daemon` as a long-lived local container. It is **opt-in**
— each plugin works standalone without it (each loads its own embedding
model in-process). The shared daemon exists for power users running
multiple plugins that benefit from a single model load + warm cache.


## When to use

Enable the shared daemon if **any** of these apply:

- You run wet + mnemo + crg concurrently and want lower RAM usage.
- Your machine has < 16 GB RAM and you want headroom for IDE / browser.
- You want the embedding model warm across plugin restarts (faster cold
  start when Claude Code re-spawns a plugin).

Skip the shared daemon if:

- You only run one of the three plugins.
- You have plenty of RAM (≥ 32 GB) and prefer fewer moving parts.
- You cannot run Docker on your machine.


## Operations

### Stop the daemon

```bash
cd ~/projects/mcp-core/docs/shared-services
docker compose down
```

Plugins fall back to in-process embedding on the next request.

### Update the daemon

```bash
cd ~/projects/mcp-core/docs/shared-services
docker compose pull
docker compose up -d
```

### View logs

```bash
docker compose logs -f embedding-daemon
```

### Cache location

The embedding model + warm cache live in the named volume
`embedding-cache`. Inspect it:

```bash
docker volume inspect shared-services_embedding-cache
```

To wipe it (forces re-download on next start):

```bash
docker compose down -v
```


## References

- `mcp-core/packages/embedding-daemon/` — source for the daemon itself.
- Migration doc: `~/projects/mcp-core/docs/migration-2026-04-30.md` —
  context for the multi-mode architecture this slot-fits into.


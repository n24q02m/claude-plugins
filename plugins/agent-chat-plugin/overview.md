# Agent Chat -- Overview

Agent Chat is a portable CLI/Skill coordination layer for peer AI-agent sessions. It uses human-readable Markdown and JSON files in a shared folder; it is not an MCP server and does not execute agents, choose models, approve permissions, or run a hosted coordinator.

## What it does

- Exchanges ordered Markdown messages with per-agent read cursors and token-free waiting.
- Tracks structured tasks, dependency readiness, owners, leases, and explicit stale recovery.
- Coordinates exclusive workspace-relative path locks with traversal and symlink-escape protection.
- Derives a deterministic `state.md` summary without deleting authoritative messages, tasks, claims, or locks.
- Publishes versioned capability and status events for adapter-neutral handshakes.

## Distribution boundary

The portable CLI/Skill is the primary contract and works from a generic shell or any harness that can invoke it. This marketplace also ships a Claude Code plugin adapter with lifecycle hooks and a command. Portable compatibility is not a claim of first-class native integration in every harness.

Agent Chat has no MCP transport, wake bridge, network daemon, credential store, or remote service. Those remain separate design decisions.

## Next steps

- [Setup](/servers/agent-chat-plugin/setup/) -- install the portable CLI/Skill or the Claude plugin adapter.
- [Commands](/servers/agent-chat-plugin/tools/) -- task, lease, lock, state, message, and event commands.

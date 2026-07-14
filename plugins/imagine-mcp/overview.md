# Imagine MCP -- Overview

Image and video understanding and generation for AI agents, using your own provider API keys. One server for "look at this media and tell me X" and "make an image or video from this prompt".

## What it does

- **Understand**: answer a prompt about one or more image/video URLs in a single call (mixed image+video where the chosen provider supports it).
- **Generate**: create an image, or a video, from a text prompt. Video generation is asynchronous -- the first call returns a job id, and you poll with that id until the render completes.
- Optional reference image, aspect ratio, and duration controls, plus a response cache.

## Tools

Two single-purpose tools -- `understand` and `generate` -- plus the universal `config` (an `action`-driven dispatcher covering credentials, runtime settings, and status) and `help`; `config__open_relay` reopens the browser credential form. Every parameter is listed in the [tools reference](/servers/imagine-mcp/tools/).

## Clients

Defaults to `local-relay` for a single-user browser credential flow and also runs over stdio; self-host the HTTP build for claude.ai web compatibility and multi-user isolation. Works with any MCP client -- Claude Code, Codex, Gemini CLI, Cursor, and Windsurf. See the [modes overview](/get-started/modes-overview/).

## Configuration

Bring your own provider API keys (`XAI_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`), supplied via the browser relay form or environment variables -- with none configured the server reports a degraded state. A default provider and quality tier are runtime settings you can change through the `config` tool. Use placeholders in shared config and never commit real keys. Full walkthrough in [setup](/servers/imagine-mcp/setup/).

## Next steps

- [Setup](/servers/imagine-mcp/setup/) -- install and configure
- [Tools reference](/servers/imagine-mcp/tools/) -- every parameter
- [Troubleshooting](/servers/imagine-mcp/troubleshooting/)

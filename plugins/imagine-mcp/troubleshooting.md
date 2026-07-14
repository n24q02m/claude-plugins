# Imagine MCP -- Troubleshooting

Common issues specific to imagine-mcp. For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `uvx`/`pip` will not pick a prerelease unless you pin the exact version:

```sh
uvx imagine-mcp@<X.Y.0bN>
```

Replace `<X.Y.0bN>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Tools return a degraded / no-credentials state

`understand` and `generate` need at least one provider API key. With none configured the server reports a degraded state. Check what is loaded:

```
config(action="status")
```

Then supply a key (`XAI_API_KEY`, `GEMINI_API_KEY`, or `OPENAI_API_KEY`) via the relay form or an environment variable and re-run `config(action="relay_complete")`.

## Video generation never finishes

Video generation is asynchronous. The first `generate(media_type="video", ...)` call returns a `job_id`; call `generate` again with that same `job_id` to poll until the render completes. Do not expect the first call to return the finished video.

## Wrong provider or quality used

`provider`, `model`, and `tier` can be overridden per call, or set defaults with `config(action="set", key="default_provider" | "default_tier", value=...)`. Not every provider supports video or mixed image+video understanding.

## Credentials or settings not saving

- Under stdio there is no browser relay form -- `config__open_relay` returns `stdio_unsupported`. Set keys as environment variables or `userConfig` fields.
- In HTTP/local-relay mode, check `config(action="relay_status")` and reset with `config(action="relay_reset")` if it seems stuck.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker/HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/imagine-mcp/setup/).

## Filing a bug

Open an issue on [n24q02m/imagine-mcp](https://github.com/n24q02m/imagine-mcp) with your OS, server version, transport mode, and the last 50 lines of stderr.

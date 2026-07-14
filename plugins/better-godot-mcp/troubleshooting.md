# Better Godot MCP -- Troubleshooting

Common issues specific to better-godot-mcp. For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

New features often ship as a beta before the stable release. `npm`/`npx` will not pick a prerelease unless you pin the exact version:

```sh
npx better-godot-mcp@<X.Y.Z-beta.N>
```

Replace `<X.Y.Z-beta.N>` with the exact beta version. Drop the `@<version>` suffix to return to the latest stable.

## Godot engine not found

The server needs a Godot binary. If `project`/`scenes` actions fail to spawn the engine, point it explicitly with `GODOT_PATH` (and `GODOT_PROJECT_PATH` for the project root), or let the server locate an install:

```
config(action="detect_godot")
config(action="check")
```

## Some tilemap / animation actions only return guidance text

`animation`'s `add_keyframe` and `tilemap`'s `set_tile`/`paint` currently return static guidance rather than writing the change -- binary tile-map and keyframe data is not yet writable through this interface. Use the returned guidance to make the edit in the Godot editor.

## No relay form appears

better-godot-mcp is **stdio-only by default** and needs no credentials, so there is no hosted relay/OAuth flow -- `config__open_relay` does not apply. If you self-host the Docker `:http` build, configuration is still credential-free.

## Reading a scene's run output

`project(action="run")` captures stdout/stderr into a per-PID ring buffer. Read it with `project(action="logs")` (optionally pass a `pid`; it defaults to the most recently started process and keeps logs for the last 10 exited processes).

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker override loads both. Pick one method and uninstall the other. See [setup](/servers/better-godot-mcp/setup/).

## Filing a bug

Open an issue on [n24q02m/better-godot-mcp](https://github.com/n24q02m/better-godot-mcp) with your OS, server version, transport mode, and the last 50 lines of stderr.

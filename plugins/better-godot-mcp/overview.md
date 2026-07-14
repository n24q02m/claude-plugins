# Better Godot MCP -- Overview

Godot Engine automation for AI-assisted game development. Drive scenes, nodes, scripts, and a dozen more engine subsystems from an AI agent -- no credentials, just a local Godot install.

## What it does

- **Project and editor**: read project metadata and engine version, run a scene and capture its output, export, and launch or check the editor.
- **Scene authoring**: create and edit `.tscn` scenes, add/remove/configure nodes, and write GDScript.
- **Subsystems**: resources, input map, signals, animation, tilemap, shaders, physics, audio, navigation, and Control-node UI.
- All tools that return project file content are wrapped in an XPIA safety marker to defend against injection via a poisoned project's files.

## Tools

Fourteen content-bearing composite tools (`project`, `scenes`, `nodes`, `scripts`, `resources`, `input_map`, `signals`, `animation`, `tilemap`, `shader`, `physics`, `audio`, `navigation`, `ui`), each driven by an `action` parameter, plus `editor` (launch/status), the universal `config`, and `help`. Every action and parameter is listed in the [tools reference](/servers/better-godot-mcp/tools/).

## Clients

Defaults to `stdio` -- it spawns a local Godot process and needs no hosted credential relay or OAuth. Docker `:http` builds exist for advanced self-host, but there is no hosted remote-relay mode. Works with any stdio MCP client -- Claude Code, Codex, Gemini CLI, Cursor, and Windsurf. See the [modes overview](/get-started/modes-overview/).

## Configuration

No credentials. Point the server at your engine and project with the `GODOT_PATH` and `GODOT_PROJECT_PATH` environment variables; the `config` tool's `detect_godot` action can locate an installed engine for you. Full walkthrough in [setup](/servers/better-godot-mcp/setup/).

## Next steps

- [Setup](/servers/better-godot-mcp/setup/) -- install and configure
- [Tools reference](/servers/better-godot-mcp/tools/) -- every action and parameter
- [Troubleshooting](/servers/better-godot-mcp/troubleshooting/)

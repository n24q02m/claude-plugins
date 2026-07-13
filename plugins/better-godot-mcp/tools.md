# Better Godot MCP -- Tools Reference

better-godot-mcp exposes Godot Engine integration through 14 composite tools driven by an `action` parameter, plus `editor` (launch/status), `config` (credential-free server settings), and `help`. All 14 content-bearing tools wrap their results in an XPIA safety marker -- `<untrusted_godot_content>` boundary tags plus an instruction to treat the content as data, not commands -- to defend against indirect prompt injection via a poisoned project's files. `editor`, `config`, and `help` are not wrapped (they return no project file content).

| Tool | Purpose | Actions | Wrapped |
|---|---|---|---|
| `project` | Project-level operations | `info` (metadata), `version` (engine version), `run` (launch, needs `scene_path`), `stop`, `settings_get`/`settings_set` (`key` req), `export` (`preset`, `output_path` req) | Yes |
| `scenes` | `.tscn` scene CRUD | `create` (`scene_path` req; `root_type` default `Node2D`), `list`, `info`, `delete`, `duplicate` (`new_path`), `set_main` | Yes |
| `nodes` | Scene node operations | `add` (`name` req; `type` default `Node`, `parent` default `.`), `remove`, `rename` (`new_name`), `list`, `set_property`/`get_property` (`property` req) | Yes |
| `scripts` | GDScript CRUD | `create` (`script_path` req; `extends` default `Node`), `read`, `write` (`content` req), `attach` (`scene_path`, `node_name` req), `list`, `delete` | Yes |
| `resources` | Resource management | `list` (`type`: image\|audio\|font\|shader\|scene\|resource), `info`, `delete`, `import_config` | Yes |
| `input_map` | Input action bindings | `list`, `add_action` (`action_name` req; `deadzone` default 0.5), `remove_action`, `add_event` (`event_type`: key\|mouse\|joypad) | Yes |
| `signals` | Signal connections | `list` (`scene_path` req), `connect`/`disconnect` (`signal`, `from`, `to`, `method` req) | Yes |
| `animation` | AnimationPlayer setup | `create_player`, `add_animation` (`duration` default 1.0, `loop` default `true`), `add_track`, `add_keyframe`, `list` | Yes |
| `tilemap` | TileSet/TileMap setup | `create_tileset` (`tile_size` default 16), `add_source`, `set_tile`, `paint`, `list` | Yes |
| `shader` | Shader file CRUD | `create` (`shader_type`: canvas_item\|spatial\|particles\|sky\|fog), `read`, `write`, `get_params`, `list` | Yes |
| `physics` | Physics/collision setup | `layers`, `collision_setup`, `body_config` (`gravity_scale`/`mass`/`linear_damp`/`angular_damp`/`freeze`), `set_layer_name` (`dimension`: 2d\|3d) | Yes |
| `audio` | Audio bus and stream setup | `list_buses`, `add_bus` (`send_to` default `Master`), `add_effect` (`effect_type` auto-prefixed to `AudioEffect*`), `create_stream` (`stream_type` default `2D`) | Yes |
| `navigation` | Navigation region/agent/obstacle setup | `create_region` (`dimension` default `3D`), `add_agent` (`radius`/`max_speed`/etc), `add_obstacle` | Yes |
| `ui` | Control node UI setup | `create_control` (`type` default `Control`, optional `properties` object), `set_theme` (`font_size` default 16), `layout` (`preset`: full_rect\|center\|top_wide\|bottom_wide\|left_wide\|right_wide), `list_controls` | Yes |
| `editor` | Editor process control | `launch`, `status` (both take optional `project_path`) | No |
| `config` | Server config/environment | `status`, `set` (`key`, `value`), `detect_godot`, `check` | No |
| `help` | Full documentation for a tool | takes `tool_name` (enum of the 16 other tool names), not an `action` param | No |

Note: `animation`'s `add_keyframe` and `tilemap`'s `set_tile`/`paint` currently return static guidance text rather than performing the edit directly (binary tile-map/keyframe data isn't yet writable through this interface).

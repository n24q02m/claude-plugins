# Imagine MCP -- Tools Reference

imagine-mcp exposes AI image/video understanding and generation through 2 single-purpose tools (`understand`, `generate`), plus `config` (credentials + settings, itself an `action`-driven dispatcher), `help`, and `config__open_relay`. None of these tools wrap results as external/untrusted content.

## understand

Understand images and/or videos (multiple URLs in one call) given a prompt. Gemini supports mixed image+video in a single call; OpenAI/Grok are image-only. No `action` parameter.

| Parameter | Required | Notes |
|---|---|---|
| `media_urls` | Yes | List of image/video URLs; capped by `max_media_urls` |
| `prompt` | Yes | What to ask about the media |
| `provider` | No | Override provider (defaults to the configured tier's default) |
| `model` | No | `provider/model` override, bypasses the tier catalog |
| `tier` | No | Quality tier, default `poor` |
| `max_tokens` | No | Default 2048 |

## generate

Generate an image or video from a text prompt. Video generation is async: the first call returns a `job_id`; call again with that `job_id` to poll for completion. No `action` parameter.

| Parameter | Required | Notes |
|---|---|---|
| `media_type` | Yes | `image` \| `video` |
| `prompt` | Yes | Text prompt |
| `provider` / `model` / `tier` | No | Same override semantics as `understand`, default tier `poor` |
| `reference_image_url` | No | Reference/conditioning image |
| `job_id` | No | Poll an in-flight async video job |
| `output_mode` | No | `base64` \| `path` \| `both` (default) |
| `aspect_ratio` | No | Default `16:9` |
| `duration_seconds` | No | Default 8 (video) |

## config

Server configuration and credential setup, merged into one tool.

| Action | Purpose | Key parameters |
|---|---|---|
| `open_relay` | Force credential setup; returns `degraded` if none loaded, else `saved` + configured providers | -- |
| `relay_status` | Show `configured`/`pending` + live configured providers | -- |
| `relay_complete` | Show `saved`/`no_credentials` + live configured providers | -- |
| `relay_skip` | Check env-var-only providers; `needs_setup` if none, else `using_env` | -- |
| `relay_reset` | Reset saved credentials | -- |
| `warmup` | No-op (no heavy resources to warm up) | -- |
| `status` | Show version, credential state, configured providers, default provider/tier, cache TTL | -- |
| `set` | Update a runtime setting (`log_level`, `default_provider`, `default_tier`, `cache_ttl_seconds`) | `key`, `value` (required) |
| `cache_clear` | Clear the response cache | -- |

## help

Get full documentation for a topic.

| Parameter | Values |
|---|---|
| `topic` | `understand` (default) \| `generate` \| `config` |

## config__open_relay

Opens the relay configuration form in the user's browser. Returns the relay URL, whether the browser launched, and credential status (`configured`\|`unconfigured`\|`expired`\|`session_active`\|`stdio_unsupported`). No parameters.

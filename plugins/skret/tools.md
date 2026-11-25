# skret -- Tools Reference

`skret mcp` exposes 8 tools. Read/health tools return key names or metadata except `skret_get`, which is the only tool that returns a secret value. Write tools (`skret_set`, `skret_delete`, `skret_rotate`) require both `mcp.allow_write: true` in `.skret.yaml` and `"confirm": true`.

## skret_list

List skret secret key names for an environment (names only, no secret values). Output: JSON array of key names.

| Parameter | Required | Description |
|---|---|---|
| `env` | No | Target environment name. Defaults to the server's resolved `default_env` |

## skret_get

Read one skret secret value by key. This is the only tool that returns secret values. Output: raw secret text.

| Parameter | Required | Description |
|---|---|---|
| `key` | Yes | Secret key name |
| `env` | No | Target environment name. Defaults to resolved environment |

## skret_env

List the skret environments accessible to this server. Output: JSON object `{environments: [...], default_env}`.

No parameters.

## skret_status

Report `skret mcp` server health: resolved environment, provider, config file path, `allow_write` flag, `allowed_envs`, and read-only state. Performs no network calls and returns no secret values.

No parameters.

## skret_doctor

Alias for `skret_status`. Reports resolved configuration and write-policy health metadata with no network calls.

No parameters.

## skret_set

Create or update a skret secret. Requires `mcp.allow_write: true` in `.skret.yaml` and `"confirm": true`.

| Parameter | Required | Description |
|---|---|---|
| `key` | Yes | Secret key name |
| `value` | Yes | Secret value to store |
| `confirm` | Yes | Must be boolean `true` |
| `env` | No | Target environment name |

## skret_delete

Delete a skret secret. Requires `mcp.allow_write: true` in `.skret.yaml` and `"confirm": true`.

| Parameter | Required | Description |
|---|---|---|
| `key` | Yes | Secret key name |
| `confirm` | Yes | Must be boolean `true` |
| `env` | No | Target environment name |

## skret_rotate

Replace a skret secret's value with an explicit new value (recorded as a rotation in the audit trail). Requires `mcp.allow_write: true` in `.skret.yaml` and `"confirm": true`.

| Parameter | Required | Description |
|---|---|---|
| `key` | Yes | Secret key name |
| `value` | Yes | Replacement secret value |
| `confirm` | Yes | Must be boolean `true` |
| `env` | No | Target environment name |

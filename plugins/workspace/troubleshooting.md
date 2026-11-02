# Workspace MCP -- Troubleshooting

Common issues specific to better-workspace-mcp. For problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

This server currently publishes **only** beta builds -- there is no stable tag yet. The npm `latest` and `beta` dist-tags both point at the newest beta, so `@latest` works today. To pin an exact build:

```sh
npx @n24q02m/workspace@<X.Y.Z-beta.N>
```

Once a stable release exists, `latest` will move to it and prereleases will need the explicit `@<X.Y.Z-beta.N>` pin again.

## "Access blocked: This app is not verified"

Your OAuth consent screen is still unpublished. Add your Google account as a test user in the Cloud Console (APIs & Services > OAuth consent screen > Test users), or publish the consent screen.

## `redirect_uri_mismatch`

Google binds redirect URIs to the OAuth client **type**. Stdio needs a **Desktop app** client, because consent returns to a loopback address. HTTP needs a **Web application** client; a Desktop client will fail there. Do not point one machine's stdio and HTTP deploys at the same client. If the type is right, check the Web client's authorized redirect URIs against the one named in Google's error page, matching scheme and path exactly.

## The browser never opens on first run

Containers and headless hosts have no browser to open. Either authorize once via a plugin/`npx` install on a workstation and mount the resulting `~/.better-workspace` directory into the container (the stored refresh token is reused afterwards), or run HTTP mode and consent with `workspace auth --user <namespace>` on the server host. `MCP_NO_BROWSER=1` suppresses the launch attempt explicitly.

## A Workspace API returns 403

The API is most likely not enabled on your Cloud project -- enable it under APIs & Services > Library and retry.

If the API *is* enabled, the scope set is the next suspect: scopes are requested at consent time, so an account authorized before a scope was added keeps the old set. Re-consent with `config(action="account_add")` for that account.

## Calls act on the wrong account

Pass `account="<email>"` explicitly on the call. `config(action="account_list")` shows every configured account and which is primary; `config(action="account_set_default", account="<email>")` changes it.

Naming an account that is not configured returns an error naming it -- the call is never rerouted to the primary, so a wrong-account result means the wrong `account` was passed or omitted.

## `config(action="status")` still says `awaiting_setup`

The consent never completed. In stdio, re-run the flow with `config(action="setup_start", force=true)` or run `workspace auth` on the host. In HTTP, consent is not served over the endpoint: run `workspace auth --user <namespace>` on the server host for that user. If consent completed but the state did not move, call `config(action="setup_complete")` to re-check.

## Docker container starts in HTTP mode when you wanted stdio

Published images are built from the last Dockerfile stage, `http`, so `MCP_TRANSPORT=http` and `PORT=8080` are baked in, and there is no separate `:stdio` tag. Override it on the run: `docker run -i --rm -e MCP_TRANSPORT=stdio n24q02m/workspace:<version>`. See [setup](/servers/workspace/setup/).

## HTTP requests are rejected with 401

In HTTP mode every request must carry `Authorization: Bearer <your-token>`, and the token must be listed in the users file (`WORKSPACE_USERS_FILE`). A 401 on the endpoint means the token is missing, wrong, or not in that file. Credentials for a user are isolated per namespace, so a valid token with no consent yet reports `awaiting_setup` instead; run `workspace auth --user <namespace>` on the host.

## HTTP server refuses to start

Startup fails when `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, or `CREDENTIAL_SECRET` is missing. Set all three, and keep `CREDENTIAL_SECRET` stable across restarts: changing it makes previously stored credentials unreadable.

## Adding questions to a form does nothing

`forms(action="create")` takes only a title. Questions are added afterwards with `forms(action="batchUpdate")`. Responses are read-only -- the Forms API cannot create one -- and listing or deleting forms goes through `drive`, not `forms`.

## Writing to a spreadsheet fails

`sheets` is read-only: `getText`, `getRange`, and `getMetadata` only. There is no write action.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker or HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/workspace/setup/).

## Filing a bug

Open an issue on [n24q02m/workspace](https://github.com/n24q02m/workspace) with your OS, server version, transport mode, and the last 50 lines of stderr.

# Better Workspace MCP -- Troubleshooting

Common issues specific to better-workspace-mcp. For daemon, lock-file, and general relay problems shared across the stack, see the [general troubleshooting guide](/get-started/troubleshooting/).

## Installing a prerelease (beta) build

This server currently publishes **only** beta builds -- there is no stable tag yet. The npm `latest` and `beta` dist-tags both point at the newest beta, so `@latest` works today. To pin an exact build:

```sh
npx @n24q02m/better-workspace-mcp@<X.Y.Z-beta.N>
```

Once a stable release exists, `latest` will move to it and prereleases will need the explicit `@<X.Y.Z-beta.N>` pin again.

## "Access blocked: This app is not verified"

Your OAuth consent screen is still unpublished. Add your Google account as a test user in the Cloud Console (APIs & Services → OAuth consent screen → Test users), or publish the consent screen.

## `redirect_uri_mismatch` in HTTP mode

Two separate causes:

- The **client type is wrong**. HTTP mode needs a **Web application** client; a Desktop client will always fail here. Stdio needs the opposite -- Desktop, because consent returns to a loopback address.
- The **redirect URI is not registered**. Add `https://<your-host>/accounts/callback` to the Web client's authorized redirect URIs, matching scheme and path exactly.

## The browser never opens on first run

Containers and headless hosts have no browser to open. Either authorize once via a plugin/`npx` install on a workstation (the stored refresh token is reused afterwards), or run HTTP mode, where each user consents at the server's own `/authorize`. `MCP_NO_BROWSER=1` suppresses the launch attempt explicitly.

## A Workspace API returns 403

The API is most likely not enabled on your Cloud project -- enable it under APIs & Services → Library and retry.

If the API *is* enabled, the scope set is the next suspect: scopes are requested at consent time, so an account authorized before a scope was added keeps the old set. Re-consent with `config(action="account_add")` for that account.

## Calls act on the wrong account

Pass `account="<email>"` explicitly on the call. `config(action="account_list")` shows every configured account and which is primary; `config(action="account_set_default", account="<email>")` changes it.

Naming an account that is not configured returns an error naming it -- the call is never rerouted to the primary, so a wrong-account result means the wrong `account` was passed or omitted.

## `config(action="status")` still says `awaiting_setup`

The consent never completed. In stdio, re-run the flow with `config(action="setup_start", force=true)`. In HTTP, open `/authorize` on your deployment. If consent completed but the state did not move, call `config(action="setup_complete")` to re-check.

## Docker container starts in HTTP mode when you wanted stdio

The published image is built from the Dockerfile's `http` stage, so `MCP_TRANSPORT=http` and `PORT=8080` are baked in, and there is no separate `:stdio` tag. Override it on the run: `docker run -i --rm -e MCP_TRANSPORT=stdio n24q02m/better-workspace-mcp:beta`. See [setup](/servers/better-workspace-mcp/setup/).

## Anyone can reach `/authorize` on my deployment

Set `MCP_RELAY_PASSWORD`. Without it, a public deployment lets anyone who discovers the URL open a session -- per-user credential isolation limits what each session can see, not who gets one. It is safe to omit only when `PUBLIC_URL` is localhost.

## Adding questions to a form does nothing

`forms(action="create")` takes only a title. Questions are added afterwards with `forms(action="batchUpdate")`. Responses are read-only -- the Forms API cannot create one -- and listing or deleting forms goes through `drive`, not `forms`.

## Writing to a spreadsheet fails

`sheets` is read-only: `getText`, `getRange`, and `getMetadata` only. There is no write action.

## Transport mismatch / duplicate entries in `/mcp`

Claude Code matches MCP servers by **endpoint**, not by name. Installing the plugin *and* adding a Docker or HTTP override loads both. Pick one method and uninstall the other. See [setup](/servers/better-workspace-mcp/setup/).

## Filing a bug

Open an issue on [n24q02m/better-workspace-mcp](https://github.com/n24q02m/better-workspace-mcp) with your OS, server version, transport mode, and the last 50 lines of stderr.

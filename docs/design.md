# Writeo MCP: design

Date: 2026-11-09

## Goal

Let Claude co-work with the user inside their Writeo account (studio.writeo.app), the way a collaborator works in a shared document: read what the user has written, and add or edit alongside them. The integration is an unofficial local MCP server. It uses Writeo's own web API and only ever touches the signed-in user's account.

## Scope

In scope, in build order:

1. Login and session handling
2. Novels: list, select, get, create, update
3. Chapters: list, get, create, update, delete
4. Characters: list, get, create, update, delete
5. Notes: list, get, create, update, delete
6. Mood board (boards): list, get, add, move, delete items

Out of scope: deleting a whole novel (done on the site), scenes, volumes, relationships, goals, stats, billing, notifications, publishing, any other account's data.

## Findings that shape the design

Observed from the user's logged-in session (read-only):

- The site is a React single-page app. It calls a REST API at `https://api.writeo.app/api/...` with a JWT bearer token.
- Authentication is Supabase-style, served from `https://db.writeo.app` (`/auth/v1`). Password login and refresh-token renewal are therefore available over plain HTTPS.
- Routes seen in the site's code: `/novels`, `/novels/reorder`, `/chapters`, `/chapters/novel/{id}`, `/chapter-statuses`, `/characters`, `/characters/novel/{id}`, `/characters/sections`, `/characters/fields`, `/notes`, `/notes?novel_id=`, `/boards`, `/boards?novel_id=`, `/boards/{id}`, `/boards/entities/batch`.
- The user's account email-and-password login is enabled.

## Architecture

A Python stdio MCP server, run on the user's own computer and added to their Claude app. Dependencies: the `mcp` Python SDK (FastMCP), `httpx`, and the standard library for the login page. No browser automation.

Modules, each with one purpose:

- `config`: reads the optional config file and environment overrides (API base URL, auth base URL, anon key).
- `auth`: password login, refresh, expiry tracking, session file. Knows nothing about novels.
- `client`: one thin HTTP wrapper. Adds the bearer token, retries once after a 401 by refreshing or re-reading the session, turns every failure into a plain-language error naming the route and status.
- `loginpage`: the local login server and its single HTML page.
- `tools_novels`, `tools_chapters`, `tools_characters`, `tools_notes`, `tools_boards`: one small module per area, each a list of MCP tools over `client`.
- `state`: the currently selected novel id, held in memory.

All API knowledge (routes, field names, response shapes) lives in the tool modules and `client`. A change on Writeo's side is then a fix in one place.

## Authentication

1. `writeo_login` starts a local web server bound to `127.0.0.1` on a free port. It returns a link of the form `http://127.0.0.1:<port>/login/<random-code>`.
2. The user opens the link in their own browser and enters email and password. The form posts to the local server, which sends them to the Supabase-style token endpoint. The password is never written to disk, logged, or returned to the model.
3. On success the server saves only the access token, refresh token and expiry in `~/.writeo-mcp/session.json`, mode 0600. It shows a success message and shuts down.
4. Before each call, `auth` refreshes the token if it expires within 60 seconds. Refresh tokens rotate, so the new one is saved each time.
5. If refresh fails or no session exists, tools return: "Not signed in. Call writeo_login."
6. Safety: the server listens on loopback only, requires the random code in the path, accepts one successful login, and exits after five minutes with no login.

The Supabase public (anon) key is needed for the token endpoint. It is public by design and is read from Writeo's own site bundle on first login and cached in the config directory. An environment variable can override it.

## Login page

One self-contained HTML file with inline CSS and about thirty lines of JavaScript. No external fonts or libraries.

- Layout: a single centred card on a deep warm-dark background with a faint glow. Cream text, muted gold accent button, serif heading in the style of Writeo's own dialogs.
- Content: heading "Writeo for Claude", one line saying the password goes straight to Writeo and is not stored, visible labels, email and password fields.
- Password field: masked by default, with an SVG eye icon at its right edge that toggles visibility. The icon switches to a slashed eye when the password is shown, has an accessible label ("Show password" / "Hide password") and `aria-pressed`, and works from the keyboard.
- Password managers and paste are allowed (`autocomplete` attributes set, no paste blocking).
- Feedback: loading state on the button, then a green "Signed in, you can close this tab", or a plain error under the field ("Wrong email or password").
- Accessibility: contrast at least 4.5:1, visible focus rings, keyboard-only operation, reduced motion respected, no emoji icons.

## Tools

Session: `writeo_login`, `writeo_status`.

Novels: `list_novels`, `select_novel`, `get_novel`, `create_novel` (title, genres, synopsis, cover), `update_novel`. No delete.

Chapters: `list_chapters`, `get_chapter`, `create_chapter`, `update_chapter` (title, text, status), `delete_chapter`.

Characters: `list_characters`, `get_character`, `create_character`, `update_character` (including profile sections and fields), `delete_character`.

Notes: `list_notes`, `get_note`, `create_note`, `update_note`, `delete_note`.

Boards: `list_boards`, `get_board`, and tools to add, move and delete items.

Every tool that acts on a novel takes an optional `novel_id` and otherwise uses the selected novel. If neither exists, the tool says so.

## Safety rules

- Every delete tool takes `confirm`. Without `confirm=true` it only reports what would be deleted and changes nothing.
- Updates send only the fields the caller supplied.
- Write tools return the saved record so the caller can see what actually changed.
- Calls are sequential with no polling or bulk crawling, so traffic looks like normal use.
- Credentials and tokens are never included in tool output or logs.

## Errors

The client maps failures to short messages: not signed in, not found (with route), validation failed (with Writeo's field messages), rate limited, and Writeo unreachable. A route that no longer exists produces "Writeo route X returned 404. The site may have changed.", so a breakage is obvious and local.

## Unknowns and how they are settled

Two facts cannot be known without capturing real write calls. Both are settled in build step 1, before any tool is written for them:

- Chapter text format: if the editor stores HTML or JSON, the chapter tools accept plain text or markdown and convert it. If it stores plain text, they pass it through.
- Board item shape: the boards tools are written last, from the captured payloads. If boards turn out not to be the mood board, that area is dropped from this version and reported.

Also verified in step 1: the API accepts the access token obtained from the password login.

## Testing

- Unit tests with a fake HTTP server for `auth` (login, refresh before expiry, refresh failure) and `client` (401 retry, error mapping).
- Tool tests against recorded response fixtures, one per area.
- A live smoke test that is off unless explicitly enabled: sign in, create a throwaway novel, add and edit one chapter, character and note, then remove them.

## Build order

1. Capture real write payloads with a throwaway novel in the user's browser, and verify the token assumption.
2. `config`, `auth`, `client`, `loginpage`, `writeo_login`, `writeo_status`.
3. Novels.
4. Chapters.
5. Characters.
6. Notes.
7. Boards.
8. Installation steps and a short README.

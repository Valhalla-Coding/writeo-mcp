# writeo-mcp

An unofficial, local MCP server that lets Claude co-write with you inside **your own** [Writeo](https://studio.writeo.app) account: read what you've written, then add or edit alongside you.

It talks to the same web API the Writeo site uses. Writeo has no public API, so this can break if the site changes. Use it only on your own account, and check Writeo's terms first.

## What Claude can do

| Area | Tools |
| --- | --- |
| Sign-in | `writeo_login`, `writeo_status` |
| Novels | `list_novels`, `select_novel`, `get_novel`, `create_novel`, `update_novel` |
| Chapters | `list_chapters`, `get_chapter`, `create_chapter`, `update_chapter`, `delete_chapter` |
| Characters | `list_characters`, `get_character`, `create_character`, `update_character`, `delete_character` |
| Notes | `list_notes`, `get_note`, `create_note`, `update_note`, `delete_note` |
| Mood board | `list_boards`, `get_board`, `add_board_item`, `update_board_item`, `delete_board_item` |

Every delete needs `confirm=true`; without it the tool only says what it would delete. Deleting a whole novel is deliberately not included.

Text is plain: blank lines separate chapter paragraphs, one line per note paragraph. Covers, character portraits, scenes, volumes beyond the default, and relationships are not supported.

## Install

One command. It installs [uv](https://docs.astral.sh/uv/) if you don't have it, finds the MCP apps on your computer (Claude Desktop, Claude Code, Codex, Cursor, VS Code, OpenCode, Antigravity), and asks which ones to set up.

- **Windows (PowerShell):** `irm https://raw.githubusercontent.com/Valhalla-Coding/writeo-mcp/HEAD/install.ps1 | iex`
- **macOS / Linux:** `curl -LsSf https://raw.githubusercontent.com/Valhalla-Coding/writeo-mcp/HEAD/install.sh | sh`

At the prompt, press Enter for all, type numbers like `1 3` to pick, or `n` for none. Then restart the app and say "sign in to Writeo".

Options (after `sh -s --` on macOS/Linux, or when running `install.ps1` from a clone): `--dry-run` shows what would change, `--yes` skips the question, `--print` shows the config snippet. Re-running is safe: it keeps your other settings, saves a `.bak` copy of every file it changes, and skips files it cannot read.

If your app isn't listed, add this to its MCP settings by hand (`--print` shows it with your own uvx path):

```json
{ "mcpServers": { "writeo": { "command": "uvx", "args": ["--from", "https://github.com/Valhalla-Coding/writeo-mcp/archive/HEAD.zip", "writeo-mcp"] } } }
```

## Signing in

Claude calls `writeo_login` and gives you a link like `http://127.0.0.1:6280/login/...`. Open it in your own browser and enter your Writeo email and password. The password goes straight to Writeo; only a session token is saved, in `~/.writeo-mcp/session.json`. The page listens on your computer only, needs the random code in the link, and closes itself after you sign in (or after 5 minutes). You only sign in again if the session is revoked or unused for a long time.

Sign in with email and password. Accounts that only use "Continue with Google" would need a password set first.

## Settings (all optional)

| Variable | Default |
| --- | --- |
| `WRITEO_MCP_HOME` | `~/.writeo-mcp` |
| `WRITEO_ANON_KEY` | read from Writeo's site on first sign-in |
| `WRITEO_API_BASE`, `WRITEO_AUTH_BASE`, `WRITEO_SITE` | Writeo's production addresses |

## Development

```
.venv/bin/pip install -e .[dev]        # Windows: .venv\Scripts\pip
.venv/bin/python -m pytest              # Windows: .venv\Scripts\python
```

Tests run against fake servers and never touch your account. See `docs/design.md` for the design and `docs/api-notes.md` for what the Writeo API looks like. If Writeo changes something, errors name the route that broke, and all route knowledge lives in `src/writeo_mcp/tools_*.py` and `client.py`.

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

## Install (Windows)

```powershell
cd writeo-mcp   # the folder you cloned or downloaded
python -m venv .venv
.venv\Scripts\pip install -e .
```

Then add it to Claude.

**Claude Desktop**: open `%APPDATA%\Claude\claude_desktop_config.json` and add the following, using the full path to your own copy of the folder:

```json
{
  "mcpServers": {
    "writeo": {
      "command": "C:\\path\\to\\writeo-mcp\\.venv\\Scripts\\writeo-mcp.exe"
    }
  }
}
```

**Claude Code** (same, with your own path):

```powershell
claude mcp add writeo -- C:\path\to\writeo-mcp\.venv\Scripts\writeo-mcp.exe
```

Restart Claude, then say "sign in to Writeo".

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

```powershell
.venv\Scripts\pip install -e .[dev]
.venv\Scripts\python -m pytest
```

Tests run against fake servers and never touch your account. See `docs/design.md` for the design and `docs/api-notes.md` for what the Writeo API looks like. If Writeo changes something, errors name the route that broke, and all route knowledge lives in `src/writeo_mcp/tools_*.py` and `client.py`.

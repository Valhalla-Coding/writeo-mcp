"""Find installed MCP clients and register writeo-mcp with the ones you pick.

    uvx --from <source> writeo-mcp-setup [--dry-run] [--yes] [--print]

Clients are looked for in their usual places only; nothing is run or searched for on disk.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

NAME = "writeo"
SOURCE = os.environ.get("WRITEO_MCP_SOURCE", "https://github.com/Valhalla-Coding/writeo-mcp/archive/HEAD.zip")
ARGS = ["--from", SOURCE, "writeo-mcp"]

NEW, CONFIGURED, OUTDATED, UNREADABLE = "new", "configured", "outdated", "unreadable"
LABEL = {NEW: "will add", CONFIGURED: "already set up", OUTDATED: "will update",
         UNREADABLE: "config is not plain JSON, skipping"}


@dataclass
class Client:
    key: str
    name: str
    kind: str                  # "json" or "cli"
    path: Path | None = None   # json: config file
    style: str = "std"         # json layout: std | vscode | opencode
    cli: str | None = None     # cli: executable
    restart: str = "Restart it."


def _xdg(env): return Path(env.get("XDG_CONFIG_HOME") or Path.home() / ".config")
def _appdata(env): return Path(env.get("APPDATA") or Path.home() / "AppData" / "Roaming")


def _claude_dir(platform, env):
    if platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude"
    if platform == "win32":
        # The Microsoft Store build redirects AppData into its package folder.
        local = Path(env.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        store = sorted((local / "Packages").glob("Claude_*/LocalCache/Roaming/Claude"))
        return store[0] if store else _appdata(env) / "Claude"
    return _xdg(env) / "Claude"


def _vscode_dir(platform, env):
    if platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Code" / "User"
    return (_appdata(env) if platform == "win32" else _xdg(env)) / "Code" / "User"


def detect_clients(platform=None, env=None, which=None) -> list[Client]:
    platform, env, which = platform or sys.platform, os.environ if env is None else env, which or shutil.which
    found: list[Client] = []
    d = _claude_dir(platform, env)
    if d.is_dir():
        found.append(Client("claude-desktop", "Claude Desktop", "json", d / "claude_desktop_config.json",
                            restart="Fully quit Claude Desktop (tray icon > Quit on Windows, Cmd+Q on Mac) and reopen it."))
    if which("claude"):
        found.append(Client("claude-code", "Claude Code", "cli", cli=which("claude"), restart="Start a new Claude Code session."))
    if which("codex"):
        found.append(Client("codex", "Codex", "cli", cli=which("codex"), restart="Restart Codex."))
    if (Path.home() / ".cursor").is_dir():
        found.append(Client("cursor", "Cursor", "json", Path.home() / ".cursor" / "mcp.json", restart="Restart Cursor."))
    d = _vscode_dir(platform, env)
    if d.is_dir():
        found.append(Client("vscode", "VS Code", "json", d / "mcp.json", style="vscode",
                            restart="Restart VS Code; it may ask you to trust the server the first time."))
    oc = _xdg(env) / "opencode"
    if oc.is_dir() or which("opencode"):
        f = next((oc / n for n in ("opencode.json", "opencode.jsonc") if (oc / n).is_file()), oc / "opencode.json")
        found.append(Client("opencode", "OpenCode", "json", f, style="opencode", restart="Restart OpenCode."))
    g = Path.home() / ".gemini"
    for sub in ("config", "antigravity"):
        if (g / sub).is_dir():
            found.append(Client("antigravity", "Antigravity", "json", g / sub / "mcp_config.json", restart="Restart Antigravity."))
            break
    return found


def find_uvx(which=None) -> str | None:
    if p := (which or shutil.which)("uvx"):
        return p
    exe = "uvx.exe" if sys.platform == "win32" else "uvx"
    for d in (os.environ.get("UV_INSTALL_DIR"), os.environ.get("XDG_BIN_HOME"),
              Path.home() / ".local" / "bin", Path.home() / ".cargo" / "bin"):
        if d and (Path(d) / exe).is_file():
            return str(Path(d) / exe)
    return None


def entry_for(style: str, uvx: str) -> dict:
    if style == "vscode":
        return {"type": "stdio", "command": uvx, "args": ARGS}
    if style == "opencode":
        return {"type": "local", "command": [uvx, *ARGS], "enabled": True}
    return {"command": uvx, "args": ARGS}


def _servers_key(style): return {"vscode": "servers", "opencode": "mcp"}.get(style, "mcpServers")


def _run(cmd) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def state(c: Client, uvx: str) -> str:
    if c.kind == "cli":
        ok, out = _run([c.cli, "mcp", "get", NAME])
        if not ok:
            return NEW
        return CONFIGURED if "--from" in out and "writeo-mcp" in out else OUTDATED
    if not c.path.exists():
        return NEW
    try:
        data = json.loads(c.path.read_text(encoding="utf-8") or "{}")
        servers = data.get(_servers_key(c.style), {}) if isinstance(data, dict) else None
        if not isinstance(servers, dict):
            raise ValueError
    except ValueError:  # shortcut: JSON with comments (jsonc) is skipped, not parsed
        return UNREADABLE
    if NAME not in servers:
        return NEW
    return CONFIGURED if servers[NAME] == entry_for(c.style, uvx) else OUTDATED


def apply(c: Client, uvx: str, st: str) -> tuple[bool, str]:
    """Returns (ok, message). JSON files are backed up first and other settings are kept."""
    if c.kind == "cli":
        add = [c.cli, "mcp", "add"] + (["--scope", "user"] if c.key == "claude-code" else []) + [NAME, "--", uvx, *ARGS]
        if st == OUTDATED:
            _run([c.cli, "mcp", "remove"] + (["--scope", "user"] if c.key == "claude-code" else []) + [NAME])
        ok, out = _run(add)
        return ok, "added" if ok else f"failed: {out[:200]}"
    data, note = {}, "created"
    if c.path.exists():
        data = json.loads(c.path.read_text(encoding="utf-8") or "{}")
        bak = c.path.with_name(c.path.name + ".bak")
        shutil.copy2(c.path, bak)
        note = f"updated (backup: {bak})"
    data.setdefault(_servers_key(c.style), {})[NAME] = entry_for(c.style, uvx)
    c.path.parent.mkdir(parents=True, exist_ok=True)
    c.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return True, note


def parse_selection(answer: str, count: int) -> list[int] | None:
    """'' / all / y -> everything, n / none -> nothing, '1 3' or '1,3' -> those; None if invalid."""
    a = answer.strip().lower()
    if a in ("", "a", "all", "y", "yes"):
        return list(range(count))
    if a in ("n", "no", "none"):
        return []
    picked: list[int] = []
    for t in re.split(r"[\s,]+", a):
        if not t.isdigit() or not 1 <= int(t) <= count:
            return None
        if int(t) - 1 not in picked:
            picked.append(int(t) - 1)
    return picked


def _ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return ""


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    uvx = find_uvx() or "uvx"
    snippet = json.dumps({"mcpServers": {NAME: entry_for("std", uvx)}}, indent=2)
    if "--print" in argv:
        print(snippet)
        return 0
    dry, yes = "--dry-run" in argv, "--yes" in argv

    print("Writeo MCP setup" + (" (dry run: nothing will be changed)" if dry else "") + "\n")
    if not find_uvx():
        print("Could not find uvx. Install uv first: https://docs.astral.sh/uv/getting-started/installation/")
        return 1
    states = [(c, state(c, uvx)) for c in detect_clients()]
    if not states:
        print("No MCP clients found (Claude Desktop, Claude Code, Codex, Cursor, VS Code, OpenCode, Antigravity).")
        print("Add this to your client's MCP config by hand:\n\n" + snippet)
        return 0
    print("Found:")
    w = max(len(c.name) for c, _ in states)
    for c, s in states:
        print(f"  {c.name.ljust(w)}  {LABEL[s]}")
    todo = [(c, s) for c, s in states if s in (NEW, OUTDATED)]
    chosen = todo
    if todo and not yes and not dry and sys.stdin is not None and sys.stdin.isatty():
        print()
        for i, (c, s) in enumerate(todo, 1):
            print(f"  {i}. {c.name}" + ("  (update)" if s == OUTDATED else ""))
        while (picked := parse_selection(_ask("Configure which? [Enter = all, numbers like 1 3, n = none]: "), len(todo))) is None:
            print("  Type numbers from the list, Enter for all, or n for none.")
        chosen = [todo[i] for i in picked]
    print()
    failed = False
    for c, s in chosen:
        if dry:
            print(f"  {c.name}: {LABEL[s]}")
            continue
        ok, msg = apply(c, uvx, s)
        failed |= not ok
        print(f"  {'OK' if ok else 'FAILED'} {c.name}: {msg}")
    if chosen and not dry:
        print("\nNext:")
        for c, _ in chosen:
            print(f"  - {c.restart}")
        print("  - Then say: sign in to Writeo")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

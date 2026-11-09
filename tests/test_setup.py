import json
from pathlib import Path

import pytest

from writeo_mcp import setup as s

UVX = "/bin/uvx"


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


def names(home, **kw):
    return [c.key for c in s.detect_clients("linux", {}, kw.get("which", lambda n: None))]


def test_detects_by_usual_locations(home):
    assert names(home) == []
    (home / ".config/Claude").mkdir(parents=True)
    (home / ".cursor").mkdir()
    (home / ".config/Code/User").mkdir(parents=True)
    (home / ".gemini/antigravity").mkdir(parents=True)
    assert names(home) == ["claude-desktop", "cursor", "vscode", "antigravity"]
    assert names(home, which=lambda n: f"/x/{n}" if n in ("claude", "codex", "opencode") else None) == \
        ["claude-desktop", "claude-code", "codex", "cursor", "vscode", "opencode", "antigravity"]


def test_claude_desktop_paths_per_os(home):
    assert s._claude_dir("darwin", {}) == home / "Library/Application Support/Claude"
    assert s._claude_dir("win32", {"APPDATA": str(home / "R"), "LOCALAPPDATA": str(home / "L")}) == home / "R/Claude"
    store = home / "L/Packages/Claude_x/LocalCache/Roaming/Claude"
    store.mkdir(parents=True)
    assert s._claude_dir("win32", {"APPDATA": str(home / "R"), "LOCALAPPDATA": str(home / "L")}) == store


@pytest.mark.parametrize("style,key,shape", [
    ("std", "mcpServers", {"command": UVX, "args": s.ARGS}),
    ("vscode", "servers", {"type": "stdio", "command": UVX, "args": s.ARGS}),
    ("opencode", "mcp", {"type": "local", "command": [UVX, *s.ARGS], "enabled": True}),
])
def test_json_clients_per_layout(tmp_path, style, key, shape):
    c = s.Client("x", "X", "json", tmp_path / "c.json", style=style)
    assert s.state(c, UVX) == s.NEW
    assert s.apply(c, UVX, s.NEW)[0]
    assert json.loads(c.path.read_text())[key][s.NAME] == shape
    assert s.state(c, UVX) == s.CONFIGURED


def test_keeps_other_settings_and_backs_up(tmp_path):
    c = s.Client("x", "X", "json", tmp_path / "c.json")
    c.path.write_text(json.dumps({"theme": "dark", "mcpServers": {"other": {"command": "o"}, s.NAME: {"command": "old"}}}))
    assert s.state(c, UVX) == s.OUTDATED
    s.apply(c, UVX, s.OUTDATED)
    data = json.loads(c.path.read_text())
    assert data["theme"] == "dark" and data["mcpServers"]["other"] == {"command": "o"}
    assert json.loads((tmp_path / "c.json.bak").read_text())["mcpServers"][s.NAME] == {"command": "old"}


@pytest.mark.parametrize("text", ["{ not json", "[1]", '{"mcpServers": []}', '{ // comment\n}'])
def test_unreadable_files_are_left_alone(tmp_path, text):
    c = s.Client("x", "X", "json", tmp_path / "c.json")
    c.path.write_text(text)
    assert s.state(c, UVX) == s.UNREADABLE
    assert c.path.read_text() == text


def test_cli_client_state_and_commands(monkeypatch):
    calls = []
    out = {"get": (False, "")}
    def run(cmd):
        calls.append(cmd)
        return out["get"] if cmd[2] == "get" else (True, "")
    monkeypatch.setattr(s, "_run", run)
    c = s.Client("claude-code", "Claude Code", "cli", cli="/bin/claude")
    assert s.state(c, UVX) == s.NEW
    out["get"] = (True, "Command: /old/python")
    assert s.state(c, UVX) == s.OUTDATED
    out["get"] = (True, f"Args: {' '.join(s.ARGS)}")
    assert s.state(c, UVX) == s.CONFIGURED
    calls.clear()
    s.apply(c, UVX, s.OUTDATED)
    assert calls[0][:4] == ["/bin/claude", "mcp", "remove", "--scope"]
    assert calls[1] == ["/bin/claude", "mcp", "add", "--scope", "user", s.NAME, "--", UVX, *s.ARGS]


@pytest.mark.parametrize("answer,expected", [
    ("", [0, 1, 2]), ("all", [0, 1, 2]), ("n", []), ("1 3", [0, 2]), ("1,3,3", [0, 2]),
    ("4", None), ("0", None), ("x", None),
])
def test_selection(answer, expected):
    assert s.parse_selection(answer, 3) == expected


def test_main_dry_run_and_yes(home, monkeypatch, capsys):
    (home / ".cursor").mkdir()
    monkeypatch.setattr(s.shutil, "which", lambda n: None)
    monkeypatch.setattr(s, "find_uvx", lambda which=None: UVX)
    assert s.main(["--dry-run"]) == 0
    assert not (home / ".cursor/mcp.json").exists()
    assert s.main(["--yes"]) == 0
    assert (home / ".cursor/mcp.json").exists()
    assert s.main(["--yes"]) == 0 and "already set up" in capsys.readouterr().out

"""Where Writeo lives and where we keep the local session."""
import os
from pathlib import Path

API_BASE = os.environ.get("WRITEO_API_BASE", "https://api.writeo.app/api")
AUTH_BASE = os.environ.get("WRITEO_AUTH_BASE", "https://db.writeo.app/auth/v1")
SITE = os.environ.get("WRITEO_SITE", "https://studio.writeo.app")


def home() -> Path:
    return Path(os.environ.get("WRITEO_MCP_HOME") or Path.home() / ".writeo-mcp")


def ensure_home() -> Path:
    h = home()
    h.mkdir(parents=True, exist_ok=True)
    return h


def session_file() -> Path:
    return home() / "session.json"

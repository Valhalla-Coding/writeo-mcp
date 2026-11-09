import pytest

from helpers import FakeClient
from writeo_mcp import deps


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("WRITEO_MCP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("WRITEO_ANON_KEY", "anon-test-key")


@pytest.fixture
def use(monkeypatch):
    def _use(routes):
        fake = FakeClient(routes)
        monkeypatch.setattr(deps, "client", fake)
        monkeypatch.setattr(deps.state, "novel_id", None)
        return fake
    return _use

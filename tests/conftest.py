import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("WRITEO_MCP_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("WRITEO_ANON_KEY", "anon-test-key")

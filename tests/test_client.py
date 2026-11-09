import httpx
import pytest

from writeo_mcp.auth import NotSignedIn
from writeo_mcp.client import Client, WriteoError


class FakeAuth:
    def __init__(self, signed_in=True):
        self.signed_in, self.refreshed = signed_in, 0

    def token(self):
        if not self.signed_in:
            raise NotSignedIn()
        return "tok"

    def refresh(self):
        self.refreshed += 1


def make(handler, auth=None):
    return Client(auth or FakeAuth(), httpx.Client(transport=httpx.MockTransport(handler)))


def test_sends_bearer_token_and_parses_json():
    def handler(req):
        assert req.headers["Authorization"] == "Bearer tok"
        return httpx.Response(200, json=[{"id": 1}])

    assert make(handler).get("/novels") == [{"id": 1}]


def test_204_returns_none():
    assert make(lambda r: httpx.Response(204)).delete("/notes/1") is None


def test_401_refreshes_once_then_retries():
    state = {"n": 0}

    def handler(req):
        state["n"] += 1
        return httpx.Response(401) if state["n"] == 1 else httpx.Response(200, json={"ok": True})

    auth = FakeAuth()
    assert make(handler, auth).get("/x") == {"ok": True}
    assert auth.refreshed == 1


def test_not_signed_in_message():
    with pytest.raises(WriteoError, match="Call writeo_login"):
        make(lambda r: httpx.Response(200, json={}), FakeAuth(signed_in=False)).get("/x")


def test_missing_route_says_site_may_have_changed():
    body = {"success": False, "error": {"message": "Route not found: PATCH /api/novels/1"}}
    with pytest.raises(WriteoError, match="no longer exists"):
        make(lambda r: httpx.Response(404, json=body)).request("PATCH", "/novels/1")


def test_plain_404_validation_and_unreachable():
    with pytest.raises(WriteoError, match="Not found"):
        make(lambda r: httpx.Response(404, json={})).get("/x")
    with pytest.raises(WriteoError, match="rejected the request"):
        make(lambda r: httpx.Response(422, text="title required")).post("/x", {})

    def boom(req):
        raise httpx.ConnectError("down")

    with pytest.raises(WriteoError, match="Could not reach Writeo"):
        make(boom).get("/x")

import base64
import json
import time

import httpx
import pytest

from writeo_mcp import config
from writeo_mcp.auth import Auth, LoginFailed, NotSignedIn, find_anon_key


def make_auth(handler):
    return Auth(httpx.Client(transport=httpx.MockTransport(handler)))


def token_reply(access="a1", refresh="r1", expires_in=3600):
    return httpx.Response(200, json={"access_token": access, "refresh_token": refresh,
                                     "expires_in": expires_in, "user": {"email": "me@example.com"}})


def test_login_stores_tokens_but_not_password():
    seen = {}

    def handler(req):
        seen["grant"] = req.url.params["grant_type"]
        seen["apikey"] = req.headers["apikey"]
        return token_reply()

    auth = make_auth(handler)
    auth.login("me@example.com", "hunter2")
    raw = config.session_file().read_text()
    assert "hunter2" not in raw
    assert seen == {"grant": "password", "apikey": "anon-test-key"}
    assert auth.token() == "a1"
    assert auth.status()["email"] == "me@example.com"


def test_wrong_password():
    auth = make_auth(lambda req: httpx.Response(400, json={"error": "invalid_grant"}))
    with pytest.raises(LoginFailed, match="Wrong email or password"):
        auth.login("me@example.com", "nope")


def test_not_signed_in():
    with pytest.raises(NotSignedIn):
        make_auth(lambda req: token_reply()).token()


def test_refreshes_when_close_to_expiry_and_rotates_refresh_token():
    calls = []

    def handler(req):
        calls.append(req.url.params["grant_type"])
        body = json.loads(req.content)
        if req.url.params["grant_type"] == "refresh_token":
            assert body == {"refresh_token": "r1"}
            return token_reply("a2", "r2")
        return token_reply("a1", "r1", expires_in=10)  # already inside the 60s window

    auth = make_auth(handler)
    auth.login("me@example.com", "pw")
    assert auth.token() == "a2"
    assert calls == ["password", "refresh_token"]
    assert json.loads(config.session_file().read_text())["refresh_token"] == "r2"


def test_failed_refresh_means_sign_in_again():
    def handler(req):
        if req.url.params["grant_type"] == "refresh_token":
            return httpx.Response(400, json={})
        return token_reply(expires_in=5)

    auth = make_auth(handler)
    auth.login("me@example.com", "pw")
    with pytest.raises(NotSignedIn):
        auth.token()


def test_find_anon_key_picks_the_anon_role():
    def jwt(payload):
        enc = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
        return f"{enc({'alg': 'HS256'})}.{enc(payload)}.signaturepart1234"

    js = f'a="{jwt({"role": "service"})}";b="{jwt({"role": "anon"})}"'
    assert find_anon_key(js) == jwt({"role": "anon"})
    assert find_anon_key("nothing here") is None

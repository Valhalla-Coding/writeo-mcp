import http.client
import json

from writeo_mcp import loginpage
from writeo_mcp.auth import LoginFailed


class FakeAuth:
    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    def login(self, email, password):
        self.calls.append((email, password))
        if self.fail:
            raise LoginFailed("Wrong email or password.")


def request(url, method="GET", body=None, host=None):
    host_port = url.split("/")[2]
    path = "/" + url.split("/", 3)[3]
    conn = http.client.HTTPConnection(host_port, timeout=5)
    headers = {"Host": host or host_port}
    if body is not None:
        headers["Content-Type"] = "application/json"
    conn.request(method, path, json.dumps(body) if body is not None else None, headers)
    r = conn.getresponse()
    return r.status, r.read()


def test_page_has_masked_password_and_eye_toggle():
    url = loginpage.start(FakeAuth())
    status, body = request(url)
    html = body.decode()
    assert status == 200
    assert 'id="password" type="password"' in html
    assert 'aria-label="Show password"' in html and 'aria-pressed="false"' in html


def test_wrong_code_and_wrong_host_are_rejected():
    url = loginpage.start(FakeAuth())
    assert request(url + "x")[0] == 404
    assert request(url, host="evil.example")[0] == 404
    assert request(url + "/submit", "POST", {"email": "a", "password": "b"}, host="evil.example")[0] == 404


def test_successful_login_passes_credentials_to_auth():
    auth = FakeAuth()
    url = loginpage.start(auth)
    status, body = request(url + "/submit", "POST", {"email": " me@example.com ", "password": "pw"})
    assert status == 200 and json.loads(body) == {"ok": True}
    assert auth.calls == [("me@example.com", "pw")]


def test_failed_login_returns_readable_error():
    url = loginpage.start(FakeAuth(fail=True))
    status, body = request(url + "/submit", "POST", {"email": "a@b.c", "password": "bad"})
    assert status == 401 and json.loads(body)["error"] == "Wrong email or password."
    assert request(url + "/submit", "POST", {"nope": 1})[0] == 400

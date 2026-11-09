"""One thin HTTP wrapper for Writeo's API. All failures become WriteoError with a plain message."""
import httpx

from . import config
from .auth import Auth, NotSignedIn


class WriteoError(Exception):
    pass


class Client:
    def __init__(self, auth: Auth, http: httpx.Client | None = None):
        self.auth = auth
        self.http = http or httpx.Client(timeout=30)

    def _send(self, method, path, params, json):
        return self.http.request(method, config.API_BASE + path, params=params, json=json,
                                 headers={"Authorization": "Bearer " + self.auth.token()})

    def request(self, method: str, path: str, params=None, json=None):
        try:
            r = self._send(method, path, params, json)
            if r.status_code == 401:
                self.auth.refresh()
                r = self._send(method, path, params, json)
        except NotSignedIn:
            raise WriteoError("Not signed in. Call writeo_login.") from None
        except httpx.RequestError as e:
            raise WriteoError(f"Could not reach Writeo ({e.__class__.__name__}).") from None
        if r.status_code >= 400:
            raise WriteoError(self._explain(method, path, r))
        if r.status_code == 204 or not r.content:
            return None
        return r.json()

    @staticmethod
    def _explain(method: str, path: str, r: httpx.Response) -> str:
        s = r.status_code
        if s == 401:
            return "Writeo rejected the session. Call writeo_login."
        if s == 404 and "Route not found" in r.text:
            return f"Writeo route {method} {path} no longer exists. The site may have changed."
        if s == 404:
            return f"Not found: {method} {path}."
        if s == 429:
            return "Writeo is rate limiting requests. Wait a moment and try again."
        if s in (400, 409, 422):
            return f"Writeo rejected the request ({s}): {r.text[:300]}"
        return f"Writeo error {s} on {method} {path}."

    def get(self, path, params=None):
        return self.request("GET", path, params=params)

    def post(self, path, json):
        return self.request("POST", path, json=json)

    def put(self, path, json):
        return self.request("PUT", path, json=json)

    def delete(self, path):
        return self.request("DELETE", path)

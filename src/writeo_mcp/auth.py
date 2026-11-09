"""Sign in to Writeo's Supabase-style auth service and keep the session fresh.

Only tokens are stored (never the password), in a file only the current user can read.
"""
import base64
import json
import os
import re
import time

import httpx

from . import config


class NotSignedIn(Exception):
    pass


class LoginFailed(Exception):
    pass


def _jwt_payload(token: str) -> dict:
    part = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def find_anon_key(js: str):
    """Writeo's site ships its public (anon) key inside the main script bundle."""
    for tok in set(re.findall(r"eyJ[\w-]{10,}\.eyJ[\w-]{10,}\.[\w-]{10,}", js)):
        try:
            if _jwt_payload(tok).get("role") == "anon":
                return tok
        except Exception:
            continue
    return None


class Auth:
    def __init__(self, http: httpx.Client | None = None):
        self.http = http or httpx.Client(timeout=20)

    # -- storage
    def _load(self):
        try:
            return json.loads(config.session_file().read_text())
        except (OSError, ValueError):
            return None

    def _save(self, session: dict):
        config.ensure_home()
        path = config.session_file()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(session))
        try:
            os.chmod(tmp, 0o600)  # no-op on Windows, where the user profile is already private
        except OSError:
            pass
        os.replace(tmp, path)

    def _store(self, data: dict, email: str | None = None):
        old = self._load() or {}
        self._save({
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_at": data.get("expires_at") or int(time.time()) + int(data.get("expires_in", 3600)),
            "email": email or (data.get("user") or {}).get("email") or old.get("email"),
        })

    # -- public key
    def anon_key(self) -> str:
        key = os.environ.get("WRITEO_ANON_KEY")
        if key:
            return key
        cache = config.home() / "anon_key.txt"
        if cache.exists():
            return cache.read_text().strip()
        page = self.http.get(config.SITE + "/").text
        m = re.search(r"/static/js/main\.[\w]+\.js", page)
        key = find_anon_key(self.http.get(config.SITE + m.group(0)).text) if m else None
        if not key:
            raise LoginFailed("Could not read Writeo's public sign-in key. The site may have changed.")
        config.ensure_home()
        cache.write_text(key)
        return key

    # -- sign in / refresh
    def _token_call(self, grant: str, body: dict) -> httpx.Response:
        return self.http.post(f"{config.AUTH_BASE}/token", params={"grant_type": grant},
                              json=body, headers={"apikey": self.anon_key()})

    def login(self, email: str, password: str):
        r = self._token_call("password", {"email": email, "password": password})
        if r.status_code in (400, 401, 422):
            raise LoginFailed("Wrong email or password.")
        if r.status_code >= 400:
            raise LoginFailed(f"Writeo sign-in failed ({r.status_code}).")
        self._store(r.json(), email)

    def refresh(self):
        s = self._load()
        if not s:
            raise NotSignedIn()
        r = self._token_call("refresh_token", {"refresh_token": s["refresh_token"]})
        if r.status_code >= 400:
            raise NotSignedIn()
        self._store(r.json())

    def token(self) -> str:
        s = self._load()
        if not s:
            raise NotSignedIn()
        if s["expires_at"] - time.time() < 60:
            self.refresh()
            s = self._load()
        return s["access_token"]

    def status(self) -> dict:
        s = self._load()
        if not s:
            return {"signed_in": False}
        return {"signed_in": True, "email": s.get("email"),
                "token_seconds_left": max(0, int(s["expires_at"] - time.time()))}

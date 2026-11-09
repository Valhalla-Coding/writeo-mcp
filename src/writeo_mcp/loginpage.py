"""A one-shot local sign-in page. Listens on 127.0.0.1 only, needs a random code in the URL,
accepts one successful login, then shuts down (or after a timeout)."""
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources

import httpx

from .auth import Auth, LoginFailed


def start(auth: Auth, timeout: float = 300) -> str:
    code = secrets.token_urlsafe(16)
    page = (resources.files("writeo_mcp") / "login.html").read_text(encoding="utf-8").encode()
    base = f"/login/{code}"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _reply(self, status, body, ctype="application/json"):
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _host_ok(self):  # blocks DNS-rebinding style requests
            return self.headers.get("Host") == f"127.0.0.1:{server.server_address[1]}"

        def do_GET(self):
            if self.path == base and self._host_ok():
                self._reply(200, page, "text/html; charset=utf-8")
            else:
                self._reply(404, b"Not found", "text/plain")

        def do_POST(self):
            if self.path != base + "/submit" or not self._host_ok():
                return self._reply(404, b"Not found", "text/plain")
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
                email, password = data["email"].strip(), data["password"]
            except (ValueError, KeyError, AttributeError):
                return self._reply(400, {"error": "Enter your email and password."})
            try:
                auth.login(email, password)
            except LoginFailed as e:
                return self._reply(401, {"error": str(e)})
            except httpx.RequestError:
                return self._reply(502, {"error": "Could not reach Writeo."})
            self._reply(200, {"ok": True})
            threading.Thread(target=server.shutdown, daemon=True).start()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    timer = threading.Timer(timeout, server.shutdown)
    timer.daemon = True
    timer.start()
    return f"http://127.0.0.1:{server.server_address[1]}{base}"

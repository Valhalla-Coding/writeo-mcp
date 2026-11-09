"""Shared test helpers."""
import asyncio
import json
from pathlib import Path

from writeo_mcp.server import mcp

FIXTURES = Path(__file__).parent / "fixtures"


class FakeClient:
    """Stands in for Client: returns canned replies by (METHOD, path) and records every call."""

    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def request(self, method, path, params=None, json=None):
        self.calls.append((method, path, params, json))
        reply = self.routes[(method, path)]
        return reply(json) if callable(reply) else reply

    def get(self, path, params=None): return self.request("GET", path, params=params)
    def post(self, path, json): return self.request("POST", path, json=json)
    def put(self, path, json): return self.request("PUT", path, json=json)
    def delete(self, path): return self.request("DELETE", path)

    def sent(self, method, path):
        return [c[3] for c in self.calls if c[0] == method and c[1] == path]


def call(name, **args):
    result = asyncio.run(mcp.call_tool(name, args))
    content = result[0] if isinstance(result, tuple) else result
    text = content[0].text
    try:
        return json.loads(text)
    except ValueError:
        return text


def fixture(name: str) -> dict:
    """A recorded Writeo request/response set from tests/fixtures/<name>.json."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))

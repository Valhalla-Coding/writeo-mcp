"""Shared singletons. Tools read these at call time so tests can swap them."""
from .auth import Auth
from .client import Client, WriteoError

auth = Auth()
client = Client(auth)


class State:
    novel_id: int | None = None


state = State()


def need_novel(novel_id: int | None = None) -> int:
    nid = novel_id or state.novel_id
    if not nid:
        raise WriteoError("No novel selected. Call select_novel, or pass novel_id.")
    return int(nid)

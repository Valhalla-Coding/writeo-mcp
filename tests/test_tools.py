import asyncio
import json

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from writeo_mcp import deps
from writeo_mcp.client import WriteoError
from writeo_mcp.server import mcp


from helpers import call  # noqa: E402


def test_every_planned_tool_exists():
    names = {t.name for t in asyncio.run(mcp.list_tools())}
    assert {"writeo_login", "writeo_status", "list_novels", "select_novel", "create_novel", "update_novel",
            "list_chapters", "get_chapter", "create_chapter", "update_chapter", "delete_chapter",
            "list_characters", "get_character", "create_character", "update_character", "delete_character",
            "list_notes", "get_note", "create_note", "update_note", "delete_note",
            "list_boards", "get_board", "add_board_item", "update_board_item", "delete_board_item"} <= names


def test_create_novel_sends_writeos_payload_and_selects_it(use):
    fake = use({("POST", "/novels"): lambda b: {"id": 7, "title": b["title"], "description": b["description"], "genre_v2": b["genre_v2"]}})
    out = call("create_novel", title="My Novel", synopsis="A short synopsis.", genres=["Fantasy"])
    body = fake.sent("POST", "/novels")[0]
    assert body["genre_v2"] == ["Fantasy"] and body["description"] == "A short synopsis." and body["cover_image_url"] == ""
    assert out["id"] == 7 and deps.state.novel_id == 7


def test_tools_need_a_novel(use):
    use({})
    with pytest.raises(ToolError, match="No novel selected"):
        call("list_chapters")


def test_create_chapter_makes_first_volume_and_converts_text(use):
    fake = use({
        ("GET", "/volumes/novel/5"): [],
        ("POST", "/volumes"): {"id": 11},
        ("GET", "/chapters/novel/5"): [],
        ("POST", "/chapters"): lambda b: {"id": 99, "title": b["title"], "content": b["content"]},
    })
    deps.state.novel_id = 5
    out = call("create_chapter", title="One", text="Hello.\n\nSecond.")
    assert fake.sent("POST", "/volumes") == [{"title": "Volume One", "volume_number": 1, "novel_id": "5"}]
    body = fake.sent("POST", "/chapters")[0]
    assert body["volume_id"] == 11 and body["order_index"] == 1 and body["novel_id"] == "5"
    assert body["content"] == "<p>Hello.</p><p>Second.</p>"
    assert out["text"] == "Hello.\n\nSecond."


def test_create_chapter_appends_to_latest_volume(use):
    fake = use({
        ("GET", "/volumes/novel/5"): [{"id": 1, "volume_number": 1}, {"id": 2, "volume_number": 2}],
        ("GET", "/chapters/novel/5"): [{"volume_id": 2}, {"volume_id": 2}, {"volume_id": 1}],
        ("POST", "/chapters"): {"id": 1, "content": ""},
    })
    deps.state.novel_id = 5
    call("create_chapter", title="Three")
    body = fake.sent("POST", "/chapters")[0]
    assert body["volume_id"] == 2 and body["order_index"] == 3


def test_update_chapter_sends_hash_only_when_text_changes(use):
    fake = use({
        ("GET", "/chapters/3"): {"id": 3, "content_hash": "h1", "content": "<p>old</p>"},
        ("PUT", "/chapters/3"): {"id": 3, "content": "<p>new</p>"},
    })
    call("update_chapter", chapter_id=3, text="new")
    assert fake.sent("PUT", "/chapters/3") == [{"content": "<p>new</p>", "base_content_hash": "h1"}]
    fake.calls.clear()
    call("update_chapter", chapter_id=3, title="Renamed")
    assert fake.sent("PUT", "/chapters/3") == [{"title": "Renamed"}]


@pytest.mark.parametrize("name,route,lookup,args", [
    ("delete_chapter", "/chapters/3", {("GET", "/chapters/3"): {"id": 3, "title": "x"}}, {"chapter_id": 3}),
    ("delete_character", "/characters/4", {("GET", "/characters/novel/5"): [{"id": 4, "name": "x"}]}, {"character_id": 4}),
    ("delete_note", "/notes/6", {("GET", "/notes"): [{"id": 6, "title": "x"}]}, {"note_id": 6}),
])
def test_deletes_need_confirm(use, name, route, lookup, args):
    fake = use({**lookup, ("DELETE", route): None})
    deps.state.novel_id = 5
    out = call(name, **args)
    assert out["deleted"] is False and fake.sent("DELETE", route) == []
    out = call(name, confirm=True, **args)
    assert out["deleted"] is True and len(fake.calls) and any(c[0] == "DELETE" for c in fake.calls)


def test_character_lookup_by_id_uses_the_novel_list(use):
    use({("GET", "/characters/novel/5"): [{"id": 1, "name": "A"}, {"id": 2, "name": "B", "role": "Main"}]})
    deps.state.novel_id = 5
    assert call("get_character", character_id=2)["name"] == "B"
    with pytest.raises(ToolError, match="not found"):
        call("get_character", character_id=9)


def test_note_text_goes_in_and_out_as_prosemirror(use):
    fake = use({
        ("POST", "/notes"): lambda b: {"id": 8, "title": b["title"], "content": json.dumps(b["content"])},
    })
    deps.state.novel_id = 5
    out = call("create_note", title="Magic", text="Fire.\nIce.")
    body = fake.sent("POST", "/notes")[0]
    assert body["content"]["type"] == "doc" and len(body["content"]["content"]) == 2
    assert body["novel_id"] == "5" and body["metadata"] == {"status": "To Do"}
    assert out["text"] == "Fire.\nIce."


BOARD = {"id": "b1", "title": "T", "version": 3, "edges": [],
         "nodes": [{"id": "n1", "type": "sticky", "position": {"x": 1, "y": 2}, "data": {"content": "hi"}}]}


def test_add_board_item_appends_and_passes_version(use):
    fake = use({("GET", "/boards/b1"): json.loads(json.dumps(BOARD)), ("PUT", "/boards/b1/canvas"): {}})
    out = call("add_board_item", board_id="b1", kind="sticky", text="New", x=10, y=20)
    sent = fake.sent("PUT", "/boards/b1/canvas")[0]
    assert sent["base_version"] == 3 and len(sent["nodes"]) == 2
    new = sent["nodes"][1]
    assert new["type"] == "sticky" and new["data"] == {"content": "New"} and new["position"] == {"x": 10, "y": 20}
    assert out["text"] == "New"


def test_board_update_and_confirmed_delete(use):
    fake = use({("GET", "/boards/b1"): json.loads(json.dumps(BOARD)), ("PUT", "/boards/b1/canvas"): {}})
    out = call("update_board_item", board_id="b1", item_id="n1", text="edited", x=50)
    node = fake.sent("PUT", "/boards/b1/canvas")[0]["nodes"][0]
    assert node["data"]["content"] == "edited" and node["position"] == {"x": 50, "y": 2}
    fake.calls.clear()
    assert call("delete_board_item", board_id="b1", item_id="n1")["deleted"] is False
    assert fake.sent("PUT", "/boards/b1/canvas") == []
    assert call("delete_board_item", board_id="b1", item_id="n1", confirm=True)["deleted"] is True
    assert fake.sent("PUT", "/boards/b1/canvas")[0]["nodes"] == []
    with pytest.raises(ToolError, match="not found"):
        call("update_board_item", board_id="b1", item_id="zzz", text="x")

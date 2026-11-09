import pytest
from mcp.server.fastmcp.exceptions import ToolError

from helpers import call, fixture

FX = fixture("volumes")
LIST = ("GET", "/volumes/novel/5")
CH = ("GET", "/chapters/novel/5")


def test_list_volumes(use):
    use({LIST: FX["list"]})
    assert [v["title"] for v in call("list_volumes", novel_id=5)] == ["Volume One", "Volume Two"]


def test_create_volume_numbers_after_last(use):
    fake = use({LIST: FX["list"], ("POST", "/volumes"): FX["create"]["response"]})
    call("create_volume", title="Volume Three", novel_id=5)
    assert fake.sent("POST", "/volumes") == [FX["create"]["request"]]


def test_rename_volume_sends_title(use):
    fake = use({LIST: FX["list"], ("PUT", "/volumes/2"): FX["list"][1]})
    call("rename_volume", volume_id=2, title="Two", novel_id=5)
    assert fake.sent("PUT", "/volumes/2") == [{"title": "Two"}]


def test_delete_volume_needs_confirm_and_reports_chapter_count(use):
    fake = use({LIST: FX["list"], CH: [{"id": 1, "volume_id": 2}, {"id": 2, "volume_id": 2}, {"id": 3, "volume_id": 1}],
                ("DELETE", "/volumes/2"): None})
    out = call("delete_volume", volume_id=2, novel_id=5)
    assert out["deleted"] is False and out["chapters_in_it"] == 2 and fake.sent("DELETE", "/volumes/2") == []
    assert call("delete_volume", volume_id=2, confirm=True, novel_id=5)["deleted"] is True
    assert any(c[:2] == ("DELETE", "/volumes/2") for c in fake.calls)


def test_unknown_volume_rejected(use):
    use({LIST: FX["list"]})
    with pytest.raises(ToolError, match="not found"):
        call("rename_volume", volume_id=9, title="x", novel_id=5)


def test_reorder_chapters_sends_increasing_keys(use):
    ch = [{"id": 11}, {"id": 12}, {"id": 13}]
    fake = use({CH: ch, **{("PATCH", f"/chapters/{i}/reorder"): FX["reorder"]["response"] for i in (11, 12, 13)}})
    call("reorder_chapters", ordered_ids=[13, 11, 12], novel_id=5)
    sent = {c[1]: c[3] for c in fake.calls if c[0] == "PATCH"}
    assert sent["/chapters/13/reorder"] == {"order_key": "aaa", "novel_id": "5"}
    assert sent["/chapters/11/reorder"]["order_key"] == "aab" and sent["/chapters/12/reorder"]["order_key"] == "aac"


def test_reorder_rejects_ids_not_in_novel(use):
    fake = use({CH: [{"id": 11}, {"id": 12}]})
    with pytest.raises(ToolError, match="exactly"):
        call("reorder_chapters", ordered_ids=[11, 99], novel_id=5)
    assert not any(c[0] == "PATCH" for c in fake.calls)


def test_reorder_novels_sends_orderedIds(use):
    fake = use({("GET", "/novels"): [{"id": 1}, {"id": 2}], ("PUT", "/novels/reorder"): {}})
    call("reorder_novels", ordered_ids=[2, 1])
    assert fake.sent("PUT", "/novels/reorder") == [{"orderedIds": [2, 1]}]
    with pytest.raises(ToolError, match="exactly"):
        call("reorder_novels", ordered_ids=[2])

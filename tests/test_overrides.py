import pytest
from mcp.server.fastmcp.exceptions import ToolError

from helpers import call, fixture

FX = fixture("overrides")
LIST = ("GET", "/characters/overrides/novel/5")


def test_list(use):
    use({LIST: FX["list"]})
    assert [o["term"] for o in call("list_name_overrides", novel_id=5)] == ["Zee", "Zed"]


def test_suppress_and_reassign_send_captured_bodies(use):
    fake = use({("POST", "/characters/overrides"): lambda b: FX[b["action"]]["response"]})
    call("add_name_override", term="Zed", action="suppress", novel_id=5)
    call("add_name_override", term="Zee", action="reassign", character_id=7, novel_id=5)
    assert fake.sent("POST", "/characters/overrides") == [FX["suppress"]["request"], FX["reassign"]["request"]]


def test_bad_action_and_missing_character_rejected_without_request(use):
    fake = use({})
    for args in ({"action": "hide"}, {"action": "reassign"}):
        with pytest.raises(ToolError):
            call("add_name_override", term="x", novel_id=5, **args)
    assert fake.calls == []


def test_delete_needs_confirm(use):
    fake = use({LIST: FX["list"], ("DELETE", "/characters/overrides/8981"): None})
    assert call("delete_name_override", override_id=8981, novel_id=5)["deleted"] is False
    assert fake.sent("DELETE", "/characters/overrides/8981") == []
    assert call("delete_name_override", override_id=8981, confirm=True, novel_id=5)["deleted"] is True
    with pytest.raises(ToolError, match="not found"):
        call("delete_name_override", override_id=1, novel_id=5)

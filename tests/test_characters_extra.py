import pytest
from mcp.server.fastmcp.exceptions import ToolError

from helpers import call, fixture

FX = fixture("character_aliases")
LIST = ("GET", "/characters/novel/5")


def test_get_character_includes_aliases_and_tracking(use):
    use({LIST: FX["list"]})
    out = call("get_character", character_id=1, novel_id=5)
    assert (out["aliases"], out["track_enabled"], out["match_mode"], out["require_capitalized"]) == (["Ay"], True, "auto", None)


def test_update_sends_aliases_and_switches(use):
    fake = use({("PUT", "/characters/1"): FX["update_response"]})
    out = call("update_character", character_id=1, aliases=["Ay", "Eh"], track_enabled=False,
               match_mode="substring", require_capitalized=True)
    assert fake.sent("PUT", "/characters/1") == [{"aliases": ["Ay", "Eh"], "track_enabled": False,
                                                  "match_mode": "substring", "require_capitalized": True}]
    assert out["aliases"] == ["Ay", "Eh"] and out["track_enabled"] is False


def test_empty_alias_list_clears_aliases(use):
    fake = use({("PUT", "/characters/1"): FX["update_response"]})
    call("update_character", character_id=1, aliases=[])
    assert fake.sent("PUT", "/characters/1") == [{"aliases": []}]


def test_update_name_only_still_sends_only_name(use):
    fake = use({("PUT", "/characters/1"): FX["update_response"]})
    call("update_character", character_id=1, name="New")
    assert fake.sent("PUT", "/characters/1") == [{"name": "New"}]


def test_aliases_with_swedish_letters_roundtrip(use):
    fake = use({("PUT", "/characters/1"): {**FX["update_response"], "aliases": ["Åsa", "Örjan"]}})
    out = call("update_character", character_id=1, aliases=["Åsa", "Örjan"])
    assert fake.sent("PUT", "/characters/1") == [{"aliases": ["Åsa", "Örjan"]}] and out["aliases"] == ["Åsa", "Örjan"]


def test_unknown_match_mode_rejected_before_any_request(use):
    fake = use({})
    with pytest.raises(ToolError, match="auto or substring"):
        call("update_character", character_id=1, match_mode="zzz")
    assert fake.calls == []

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from helpers import call, fixture

FX = fixture("profiles")
PROFILE = ("GET", "/characters/1/profile")


def test_profile_reads_sections_fields_and_values(use):
    use({PROFILE: FX["profile"]})
    out = call("get_character_profile", character_id=1)
    assert out["character"] == "Scratch A"
    assert out["sections"][0] == {"id": 10, "name": "S1b", "fields": [
        {"id": 21, "label": "Fears", "key": "fears", "type": "text", "value": None},
        {"id": 20, "label": "Wants more", "key": "wants", "type": "text", "value": "tea"}]}


def test_add_section_sends_string_character_id(use):
    fake = use({("POST", "/characters/sections"): FX["section_created"]})
    out = call("add_profile_section", character_id=1, name="S2")
    assert fake.sent("POST", "/characters/sections") == [{"character_id": "1", "section_name": "S2"}]
    assert out == {"id": 11, "name": "S2"}


def test_rename_section_sends_only_the_name(use):
    fake = use({("PUT", "/characters/sections/10"): FX["section_renamed"]})
    assert call("rename_profile_section", section_id=10, name="Renamed")["name"] == "Renamed"
    assert fake.sent("PUT", "/characters/sections/10") == [{"section_name": "Renamed"}]


def test_reorder_sections_sends_the_full_id_list(use):
    fake = use({("PUT", "/characters/sections/reorder"): {"success": True, "count": 2}})
    call("reorder_profile_sections", character_id=1, section_ids=[11, 10])
    assert fake.sent("PUT", "/characters/sections/reorder") == [{"characterId": 1, "orderedIds": [11, 10]}]


def test_add_field_makes_a_key_and_saves_the_value(use):
    fake = use({("POST", "/characters/fields"): FX["field_created"], ("POST", "/characters/values"): FX["value_saved"]})
    out = call("add_profile_field", character_id=1, section_id=10, label="Wants More", value="Åsa's tea")
    assert fake.sent("POST", "/characters/fields") == [{"section_id": 10, "field_key": "wants_more", "field_label": "Wants More", "field_type": "text"}]
    assert fake.sent("POST", "/characters/values") == [{"character_id": 1, "field_def_id": 22, "value": "Åsa's tea", "context": {}}]
    assert out["id"] == 22


def test_add_field_without_value_saves_no_value(use):
    fake = use({("POST", "/characters/fields"): FX["field_created"]})
    call("add_profile_field", character_id=1, section_id=10, label="Wants More")
    assert fake.sent("POST", "/characters/values") == []


def test_set_value_body(use):
    fake = use({("POST", "/characters/values"): FX["value_saved"]})
    assert call("set_profile_value", character_id=1, field_id=20, value="te")["value"] == "te"
    assert fake.sent("POST", "/characters/values") == [{"character_id": 1, "field_def_id": 20, "value": "te", "context": {}}]


def test_rename_field_sends_only_the_label(use):
    fake = use({("PUT", "/characters/fields/20"): FX["field_renamed"]})
    assert call("rename_profile_field", field_id=20, label="Desire")["label"] == "Desire"
    assert fake.sent("PUT", "/characters/fields/20") == [{"field_label": "Desire"}]


def test_reorder_fields_sends_positions(use):
    fake = use({("PUT", "/characters/fields/reorder"): {"success": True}})
    call("reorder_profile_fields", field_ids=[21, 20])
    assert fake.sent("PUT", "/characters/fields/reorder") == [{"updates": [{"id": 21, "display_order": 0}, {"id": 20, "display_order": 1}]}]


def test_each_delete_needs_confirm(use):
    fake = use({PROFILE: FX["profile"], ("DELETE", "/characters/sections/10"): None, ("DELETE", "/characters/fields"): None})
    out = call("delete_profile_section", character_id=1, section_id=10)
    assert out["deleted"] is False and out["would_delete"]["fields"] == 2
    out = call("delete_profile_field", character_id=1, field_id=20)
    assert out["deleted"] is False and out["would_delete"]["label"] == "Wants more"
    assert [c for c in fake.calls if c[0] == "DELETE"] == []
    assert call("delete_profile_section", character_id=1, section_id=10, confirm=True)["deleted"] is True
    assert call("delete_profile_field", character_id=1, field_id=20, confirm=True)["deleted"] is True
    assert fake.sent("DELETE", "/characters/fields") == [{"fieldIds": [20]}]


def test_unknown_section_or_field_is_a_clear_error(use):
    use({PROFILE: FX["profile"]})
    with pytest.raises(ToolError, match="not found"):
        call("delete_profile_section", character_id=1, section_id=999)
    with pytest.raises(ToolError, match="not found"):
        call("delete_profile_field", character_id=1, field_id=999)


def test_list_templates_summarises(use):
    use({("GET", "/characters/templates/all"): FX["templates"]})
    assert call("list_profile_templates") == [{"id": 3, "name": "Core", "description": "Basics", "fields": ["Wants"]}]

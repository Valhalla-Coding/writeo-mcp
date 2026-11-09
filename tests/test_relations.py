import pytest
from mcp.server.fastmcp.exceptions import ToolError

from helpers import call, fixture

FX = fixture("relations")
LIST = ("GET", "/relations/novel/5")
EMPTY = {"nodes": [], "links": []}


def test_create_sends_string_ids_and_known_fields(use):
    fake = use({LIST: EMPTY, ("POST", "/relations"): FX["create"]["response"]})
    out = call("create_relation", source_id=1, target_id=2, relation_type="friend", novel_id=5)
    assert fake.sent("POST", "/relations") == [FX["create"]["request"]]
    assert out["id"] == 10 and out["type"] == "friend"


def test_mutual_sets_is_bidirectional_and_inverse(use):
    fake = use({LIST: EMPTY, ("POST", "/relations"): FX["create"]["response"]})
    call("create_relation", source_id=1, target_id=2, relation_type="mentor", mutual=True, inverse_type="student", novel_id=5)
    body = fake.sent("POST", "/relations")[0]
    assert body["is_bidirectional"] is True and body["inverse_type"] == "student"


def test_type_over_15_chars_rejected_without_request(use):
    fake = use({})
    with pytest.raises(ToolError, match="15"):
        call("create_relation", source_id=1, target_id=2, relation_type="x" * 16, novel_id=5)
    assert fake.calls == []


@pytest.mark.parametrize("bad", [0, 11])
def test_intensity_out_of_range_rejected(use, bad):
    fake = use({})
    with pytest.raises(ToolError, match="1 and 10"):
        call("create_relation", source_id=1, target_id=2, relation_type="friend", intensity=bad, novel_id=5)
    assert fake.calls == []


def test_duplicate_pair_and_type_is_explained(use):
    fake = use({LIST: FX["list"]})
    with pytest.raises(ToolError, match="already"):
        call("create_relation", source_id=1, target_id=2, relation_type="friend", novel_id=5)
    assert fake.sent("POST", "/relations") == []


def test_list_names_characters(use):
    use({LIST: FX["list"]})
    rows = call("list_relations", novel_id=5)
    assert rows[0] == {"id": 10, "from": "Scratch A", "to": "Scratch B", "from_id": 1, "to_id": 2, "type": "friend",
                       "description": "", "intensity": 5, "mutual": False}
    assert rows[1]["mutual"] is True


def test_update_sends_only_given_fields(use):
    fake = use({LIST: FX["list"], ("PUT", "/relations/10"): FX["update"]["response"]})
    out = call("update_relation", relation_id=10, relation_type="mentor", novel_id=5)
    assert fake.sent("PUT", "/relations/10") == [{"relation_type": "mentor"}]
    assert out["type"] == "mentor"


def test_update_with_nothing_says_so(use):
    fake = use({LIST: FX["list"]})
    out = call("update_relation", relation_id=10, novel_id=5)
    assert out["changed"] is False and fake.sent("PUT", "/relations/10") == []


def test_update_to_a_duplicate_type_is_explained(use):
    use({LIST: {**FX["list"], "links": FX["list"]["links"] + [{**FX["list"]["links"][0], "id": 13, "type": "mentor"}]}})
    with pytest.raises(ToolError, match="already"):
        call("update_relation", relation_id=10, relation_type="mentor", novel_id=5)


def test_unknown_relation_id_is_a_clear_error(use):
    use({LIST: FX["list"]})
    for name in ("update_relation", "delete_relation"):
        with pytest.raises(ToolError, match="not found"):
            call(name, relation_id=999, novel_id=5, **({"description": "x"} if name == "update_relation" else {}))


def test_delete_needs_confirm(use):
    fake = use({LIST: FX["list"], ("DELETE", "/relations/11"): None})
    out = call("delete_relation", relation_id=11, novel_id=5)
    assert out["deleted"] is False and "reverse" in out["would_delete"]["note"] and fake.sent("DELETE", "/relations/11") == []
    assert call("delete_relation", relation_id=11, novel_id=5, confirm=True)["deleted"] is True
    assert len(fake.sent("DELETE", "/relations/11")) == 1

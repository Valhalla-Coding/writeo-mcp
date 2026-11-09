import json

import helpers


def test_fixture_loads_json_from_the_fixtures_dir(tmp_path, monkeypatch):
    (tmp_path / "sample.json").write_text(json.dumps({"a": 1}))
    monkeypatch.setattr(helpers, "FIXTURES", tmp_path)
    assert helpers.fixture("sample") == {"a": 1}

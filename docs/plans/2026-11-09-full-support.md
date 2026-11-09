# Writeo MCP Full Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Claude can read and edit everything a writer can edit in Writeo: relationships, aliases, character profile sections, volumes, scenes, chapter statuses, reordering, goals, calendar and to-dos.

**Architecture:** Same as v0.1: one small `tools_<area>.py` per area, each with `register(mcp)`, all calling `deps.client`. Every write format is captured from the real site on a scratch novel before its tool is written, saved as a fixture, and the tests replay that fixture.

**Tech Stack:** Python 3.10+, `mcp>=1.2,<2` (FastMCP), `httpx`, pytest.

**Spec:** `docs/specs/2026-11-09-full-support-design.md`

## Global Constraints

- Every delete tool takes `confirm: bool = False`; without `confirm=true` it returns `{"deleted": False, "would_delete": ..., "next": ...}` and sends no DELETE.
- Updates send only the fields the caller gave (`None` means "not given").
- Out of scope, no tools: billing, account deletion, feature board, streaks, achievements, deleting a whole novel, any "call any route" tool.
- Tools that act on a novel take `novel_id: int | None = None` and use `deps.need_novel(novel_id)`.
- Calls are sequential; no bulk crawling. Tokens are never printed, logged or stored in fixtures.
- Committed files contain no personal paths, names of the user's stories or real account data (fixtures use scratch data).
- Relation `relation_type` is at most 15 characters; `intensity` is 1 to 10.
- Python 3.10 floor; `mcp>=1.2,<2`.

## Review Focus

- A delete or update on an id that is not in the selected novel: a clear `WriteoError`, not a crash (tested in each area's task).
- An update called with no fields: sends nothing and says so, instead of an empty PUT.
- `relation_type` longer than 15 characters or `intensity` outside 1 to 10: rejected before any request.
- Text with quotes, newlines or non-Latin characters (the user writes Swedish) survives a create, read-back round trip.
- No novel selected and no `novel_id`: the existing "No novel selected" error, for every new tool.

## Existing interfaces (all tasks)

- `deps.client` (`get(path, params=None)`, `post(path, json)`, `put(path, json)`, `delete(path)`), `deps.need_novel(novel_id) -> int`, `WriteoError`.
- Tool module shape: see `src/writeo_mcp/tools_notes.py` (`_brief`, `_find`, `register(mcp)`, delete with confirm).
- Test helpers today live in `tests/test_tools.py` (`FakeClient`, `use`, `call`); Task 1 moves them.

---

### Task 1: Shared test helpers and the capture recipe

**Files:**
- Create: `tests/helpers.py` (move `FakeClient`, `call` here), `tests/fixtures/` (empty dir with `.gitkeep`)
- Modify: `tests/conftest.py` (add the `use` fixture), `tests/test_tools.py` (import from helpers), `docs/api-notes.md` (add "Capture recipe")

**Interfaces:**
- Produces: `helpers.FakeClient(routes)` with `.sent(method, path)`, `helpers.call(name, **args)`, fixture `use(routes)`, `helpers.fixture(name) -> dict` loading `tests/fixtures/<name>.json`.

- [ ] **Step 1: Move the helpers; run `pytest -q`. Expected: the existing 54 tests still pass.**
- [ ] **Step 2: Write the test `test_fixture_loads` in `tests/test_helpers.py`:** `helpers.fixture("sample")` returns the dict in a temp fixture file (use `monkeypatch` on the fixtures dir). Run it, see it fail, implement `fixture`, see it pass.
- [ ] **Step 3: Add "Capture recipe" to `docs/api-notes.md`:** create a scratch novel named "Scratch capture"; install a fetch/XHR recorder in the page that keeps method, path, request body and response for `api.writeo.app` calls and never the Authorization header; perform each action once through Writeo's own screens; save each as `tests/fixtures/<area>.json` with scratch data only; delete the scratch novel on the site afterwards.
- [ ] **Step 4: Commit** `refactor(tests): share helpers and document the capture recipe`.

### Task 2: Relationships

**Files:**
- Create: `src/writeo_mcp/tools_relations.py`, `tests/test_relations.py`, `tests/fixtures/relations.json`
- Modify: `src/writeo_mcp/server.py` (register module), `docs/api-notes.md`

**Interfaces:**
- Produces: tools `list_relations(novel_id=None) -> list[dict]` (readable rows: id, source, target, type, description, intensity, mutual), `create_relation(source_id: int, target_id: int, relation_type: str, description: str = "", intensity: int = 5, mutual: bool = False, inverse_type: str | None = None) -> dict`, `update_relation(relation_id: int, relation_type=None, description=None, intensity=None) -> dict`, `delete_relation(relation_id: int, confirm: bool = False) -> dict`.

- [ ] **Step 1: Capture** creating, editing and deleting one relation on the scratch novel, and listing via `GET /relations/novel/{id}`; save `relations.json`. Create body (already known): `source_character_id`, `target_character_id` (strings), `relation_type`, `description`, `intensity`, `is_bidirectional`, `inverse_type`, `visibility`, `ai_context`, `motivation_impact`.
- [ ] **Step 2: Tests** in `tests/test_relations.py`: `test_create_sends_string_ids_and_known_fields`, `test_mutual_sets_is_bidirectional`, `test_type_over_15_chars_rejected_without_request`, `test_intensity_out_of_range_rejected`, `test_update_sends_only_given_fields`, `test_update_with_nothing_says_so`, `test_delete_needs_confirm`, `test_list_names_characters`. Run: all fail.
- [ ] **Step 3: Implement** the four tools in `tools_relations.py`; `list_relations` maps ids to names using the `nodes` of the reply. Register in `server.py`; add the names to `test_every_planned_tool_exists`.
- [ ] **Step 4: Run `pytest -q`; all pass.**
- [ ] **Step 5: Commit** `feat(relations): list, create, update and delete relationships`.

### Task 3: Character aliases and name tracking

**Files:**
- Modify: `src/writeo_mcp/tools_characters.py`, `tests/test_tools.py` or new `tests/test_characters_extra.py`
- Test fixture: `tests/fixtures/character_aliases.json`

**Interfaces:**
- Consumes: the character list reply already carries `aliases` (list of str), `track_enabled`, `match_mode`, `require_capitalized`.
- Produces: `get_character` also returns those four fields; `update_character(..., aliases: list[str] | None = None, track_enabled: bool | None = None, match_mode: str | None = None, require_capitalized: bool | None = None)`.

- [ ] **Step 1: Capture** editing a character's tracked aliases and the tracking switches in Writeo; save the fixture (route and body shape).
- [ ] **Step 2: Tests:** `test_get_character_includes_aliases`, `test_update_aliases_sends_list`, `test_update_only_given_fields_still_holds`, `test_alias_with_swedish_letters_roundtrips`. Run: fail.
- [ ] **Step 3: Implement** in `tools_characters.py`; `_brief` gains the four fields; the update body uses the captured route and field names.
- [ ] **Step 4: Run `pytest -q`; pass.**
- [ ] **Step 5: Commit** `feat(characters): edit aliases and name tracking`.

### Task 4: Character profile sections, fields, values and templates

**Files:**
- Create: `src/writeo_mcp/tools_profiles.py`, `tests/test_profiles.py`, `tests/fixtures/profiles.json`
- Modify: `server.py`, `docs/api-notes.md`

**Interfaces:**
- Produces: `get_character_profile(character_id, novel_id=None) -> dict` (sections with fields and values as text), `add_profile_section(character_id, title, novel_id=None)`, `add_profile_field(section_id, label, value="")`, `set_profile_value(field_id, value)`, `rename_profile_section(section_id, title)`, `reorder_profile_sections(character_id, section_ids: list[int])`, `delete_profile_section(section_id, confirm=False)`, `delete_profile_field(field_id, confirm=False)`, `list_profile_templates()`, `apply_profile_template(character_id, template_id)`. Routes seen in the site: `/characters/sections`, `/characters/fields`, `/characters/values`, `/characters/templates`, `/characters/sections/from-template`, `.../reorder`.

- [ ] **Step 1: Capture** each action once (add section, add field, set value, rename, reorder, delete, list templates, apply template).
- [ ] **Step 2: Tests**, one per tool from the captured fixtures, plus `test_each_delete_needs_confirm` and `test_reorder_sends_full_id_list`. Run: fail.
- [ ] **Step 3: Implement** `tools_profiles.py` from the fixtures; register.
- [ ] **Step 4: `pytest -q` passes.**
- [ ] **Step 5: Commit** `feat(characters): profile sections, fields and templates`. **Then push round 1** (the user pushes) and tag `v0.2.0`.

### Task 5: Volumes

**Files:** Create `tools_volumes.py`, `tests/test_volumes.py`, `tests/fixtures/volumes.json`; modify `server.py`.

**Interfaces:** `list_volumes(novel_id=None)`, `create_volume(title, novel_id=None)`, `update_volume(volume_id, title=None)`, `delete_volume(volume_id, confirm=False)`. Routes: `GET /volumes/novel/{id}`, `POST /volumes`, `DELETE /volumes/{id}`; the update route is found by capture.

- [ ] **Step 1: Capture** list, create, rename, delete.
- [ ] **Step 2: Tests:** one per tool from the fixture, `test_delete_volume_needs_confirm`, `test_delete_reports_chapter_count_first` (the preview says how many chapters sit in the volume).
- [ ] **Step 3: Implement and register. Step 4: `pytest -q` passes.**
- [ ] **Step 5: Commit** `feat(volumes): list, create, rename and delete volumes`.

### Task 6: Scenes

**Files:** Create `tools_scenes.py`, `tests/test_scenes.py`, `tests/fixtures/scenes.json`; modify `server.py`.

**Interfaces:** `list_scenes(chapter_id)`, `create_scene(chapter_id, title, text="")`, `update_scene(scene_id, title=None, text=None)`, `delete_scene(scene_id, confirm=False)`, `merge_scenes(scene_ids: list[int], confirm=False)`. Routes: `/scenes`, `GET /scenes/chapter/{id}`, `POST /scenes/merge`. Text uses `convert.text_to_html` or `text_to_doc`, whichever the capture shows for scenes.

- [ ] **Step 1: Capture** create, edit text, merge two, delete.
- [ ] **Step 2: Tests** per tool, `test_merge_needs_confirm` (merge is destructive), `test_text_roundtrips_swedish_and_quotes`.
- [ ] **Step 3: Implement and register. Step 4: pass. Step 5: Commit** `feat(scenes): list, create, edit, merge and delete scenes`.

### Task 7: Chapter statuses and reordering

**Files:** Modify `tools_chapters.py`, `tools_novels.py`; create `tests/test_reorder.py`, `tests/fixtures/reorder.json`.

**Interfaces:** `list_chapter_statuses()`, `create_chapter_status(name, color=None)`, `update_chapter_status(status_id, name=None, color=None)`, `delete_chapter_status(status_id, confirm=False)`, `reorder_chapters(chapter_ids: list[int], novel_id=None)`, `reorder_novels(novel_ids: list[int])`. Routes: `/chapter-statuses`, `/novels/reorder`; the chapter reorder route is found by capture.

- [ ] **Step 1: Capture** each. **Step 2: Tests:** per tool, `test_reorder_rejects_ids_not_in_novel`, `test_status_delete_needs_confirm`. **Step 3: Implement.** **Step 4: pass.**
- [ ] **Step 5: Commit** `feat: chapter statuses and reordering`. **Then push round 2**, tag `v0.3.0`.

### Task 8: Goals

**Files:** Create `tools_goals.py`, `tests/test_goals.py`, `tests/fixtures/goals.json`; modify `server.py`.

**Interfaces:** `list_goals(novel_id=None)`, `goal_progress(goal_id)`, `create_goal(title, target: int, kind: str, novel_id=None)`, `update_goal(goal_id, title=None, target=None)`, `delete_goal(goal_id, confirm=False)`. Routes: `/goals`, `/goals/progress`.

- [ ] **Steps 1 to 5** as in Task 5 (capture, tests per tool plus delete-confirm, implement, pass). Commit `feat(goals): goals and progress`.

### Task 9: Calendar, reminders and to-dos

**Files:** Create `tools_calendar.py`, `tools_todos.py`, `tests/test_calendar.py`, `tests/test_todos.py`, fixtures; modify `server.py`.

**Interfaces:** `list_events(start: str | None = None, end: str | None = None)`, `create_event(title, date: str, notes="")`, `update_event(event_id, ...)`, `delete_event(event_id, confirm=False)`, `add_reminder(event_id, when: str)`, `list_todos()`, `add_todo(text)`, `update_todo(todo_id, text=None, done=None)`, `delete_todo(todo_id, confirm=False)`. Routes: `/calendar`, `/calendar/reminders`, `/home/todos`.

- [ ] **Steps 1 to 5** as above; extra test `test_dates_are_iso_strings`. Commit `feat: calendar, reminders and to-dos`. **Then push round 3**, tag `v0.4.0`.

### Task 10: Appearances and overrides, then wrap-up

**Files:** Modify `tools_profiles.py`; update `README.md` (tool table), `docs/api-notes.md`, `pyproject.toml` version.

**Interfaces:** `list_character_overrides(novel_id=None)`, `set_character_override(...)`, `delete_character_override(override_id, confirm=False)`, `add_character_appearance(character_id, chapter_id)` (shapes from capture).

- [ ] **Step 1: Capture** appearances and overrides. **Step 2: Tests** per tool and delete-confirm. **Step 3: Implement.**
- [ ] **Step 4: Update `README.md` tool table to every tool; run `pytest -q` and a grep that no tool name in `test_every_planned_tool_exists` is missing from the README; check no personal paths.**
- [ ] **Step 5: Optional live test** `tests/test_live.py` (skipped unless `WRITEO_LIVE=1`): on a scratch novel, create then read back then delete one item of each area.
- [ ] **Step 6: Commit** `feat: appearances, overrides and docs`. Push round 4, tag `v1.0.0`.

## Self-review

- Spec coverage: novels reorder (T7), volumes (T5), chapter statuses and reorder (T7), scenes (T6), aliases/sections/fields/templates (T3, T4), overrides/appearances (T10), relations (T2), goals (T8), calendar/reminders/to-dos (T9), safety and capture (global constraints, T1), four rounds (T4, T7, T9, T10).
- Names match across tasks: `confirm`, `need_novel`, `_brief`, `FakeClient`.

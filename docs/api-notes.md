# Writeo API notes

Observed from the Writeo web app (November 2026). Unofficial and may change.

- Site: `https://studio.writeo.app` (React). API: `https://api.writeo.app/api`. Auth: Supabase-style at `https://db.writeo.app/auth/v1`.
- Sign in: `POST /auth/v1/token?grant_type=password` with header `apikey: <public anon key>` and `{email, password}`. Refresh: `grant_type=refresh_token` with `{refresh_token}` (tokens rotate). Access tokens last 1 hour. The anon key is the only JWT with `role: anon` in the site's `static/js/main.*.js`.
- API calls use `Authorization: Bearer <access_token>`. No token gives 401. Unknown routes give 404 with `Route not found: <METHOD> <path>`.

## Routes used

| Area | Calls |
| --- | --- |
| Novels | `GET /novels`, `GET /novels/{id}`, `POST /novels`, `PUT /novels/{id}` (partial). `PATCH` does not exist. |
| Volumes | `GET /volumes/novel/{id}`, `POST /volumes` `{title, volume_number, novel_id}` |
| Chapters | `GET /chapters/novel/{id}`, `GET /chapters/{id}`, `POST /chapters`, `PUT /chapters/{id}` (partial), `DELETE /chapters/{id}` |
| Characters | `GET /characters/novel/{id}` (no fetch by id), `POST /characters`, `PUT /characters/{id}` (partial), `DELETE /characters/{id}` |
| Notes | `GET /notes?novel_id=`, `POST /notes`, `PUT /notes/{id}` (partial), `DELETE /notes/{id}` |
| Boards | `GET /boards?novel_id=`, `GET /boards/{id}`, `POST /boards` `{title, novel_id}`, `PUT /boards/{id}/canvas` `{nodes, edges, base_version}`, `DELETE /boards/{id}` (moves to trash) |

## Formats

- Novel: `title`, `description` (the synopsis), `genre_v2` (array of names), cover fields. Ids are integers.
- Chapter: needs a `volume_id`. `content` is HTML (`<p>..</p>`). Updating `content` needs `base_content_hash` from the chapter's current `content_hash`.
- Character: `name`, `description`, `role` (Main / Side ...), `image_url` (empty string is accepted).
- Note: `content` is a ProseMirror document `{type: "doc", content: [...]}`, sent as an object and returned as a JSON string.
- Board: ids are UUIDs. `nodes` hold `{id, type, position, style, data, measured}`. Types seen: `sticky` and `free_text` (text in `data.content`), `shape` (`data.shapeType`, text in `data.label`). The board's `version` goes back as `base_version` when saving; it increases by one per save. Free plan: 3 boards.


## Capture recipe

Used before writing any new tool, so formats are recorded and never guessed. Request bodies differ from response bodies (for example relations: the request says `source_character_id`, the response `character_source_id`).

1. Create a scratch novel named "Scratch capture" in the signed-in account.
2. In the page, wrap `fetch` and `XMLHttpRequest` so each call to `api.writeo.app` keeps its method, path, request body and response. Never keep the Authorization header.
3. Do each action once through Writeo's own screens (create, edit, reorder, delete).
4. Save the recorded calls as `tests/fixtures/<area>.json` with scratch data only: no real story text, names or ids that identify the account.
5. Delete the scratch novel on the site.

## Relations

- `GET /relations/novel/{novel_id}` returns `{nodes: [{id, name, ...}], links: [{id, source, target, type, intensity, description, is_bidirectional, linked_relation_id}]}`. `GET /relations/character/{id}` returns `{outgoing: [...], incoming: [...]}` of full records.
- `POST /relations` (201) body: `source_character_id` and `target_character_id` as strings, `relation_type` (1 to 15 chars), `description`, `intensity` (1 to 10), `is_bidirectional`, `inverse_type`, `visibility` ("public"), `ai_context`, `motivation_impact`. The reply uses `character_source_id` / `character_target_id`.
- `PUT /relations/{id}` takes any of `relation_type`, `description`, `intensity` and returns the full record. `DELETE /relations/{id}` returns 204; deleting one half of a mutual pair removes both.
- A second relation of the same type between the same pair is a 500 (`unique_relation_pair_type`); the tools check for it first.

## Character aliases and tracking

`PUT /characters/{id}` also takes `aliases` (list of strings, replaces the list), `track_enabled`, `require_capitalized` (true or null) and `match_mode`. `match_mode` accepted `auto` and `substring`; every other value tried was a 400 (the site's code hints at one more, not found). The character list reply carries all four fields.

## Character profiles

- `GET /characters/{id}/profile` returns `{character, sections: [{id, section_name, display_order, fields_count, fields: [{id, field_key, field_label, field_type, display_order, value}]}]}`. Values come back inside the fields.
- `POST /characters/sections` `{character_id (string), section_name}` (201). `PUT /characters/sections/{id}` `{section_name}`. `PUT /characters/sections/reorder` `{characterId, orderedIds}`. `DELETE /characters/sections/{id}` (204).
- `POST /characters/fields` `{section_id, field_key, field_label, field_type}` (201; `field_key` is required, duplicates allowed). `PUT /characters/fields/{id}` `{field_label}`. `PUT /characters/fields/reorder` `{updates: [{id, display_order}]}`. `DELETE /characters/fields` with body `{fieldIds: [..]}` (there is no per-id delete route).
- `POST /characters/values` `{character_id, field_def_id, value, context: {}}` saves a value (200, `version` increases).
- `GET /characters/templates/all` lists templates. Applying (`POST /characters/sections/from-template`) and creating templates answered 500 (bigint "undefined") for every body tried, so those are not supported.

## Volumes and ordering (captured on a scratch novel)
- `GET /volumes/novel/{id}` list; `POST /volumes` {novel_id (string), title, volume_number} 201; `PUT /volumes/{id}` {title} 200 (PATCH 404); `DELETE /volumes/{id}` 204.
- Chapter order: `PATCH /chapters/{id}/reorder` {order_key, novel_id (string)}. order_key is 1-50 lowercase letters, sorted as a string; nothing sorts before "a", so the tool rewrites every chapter with fixed-width keys (aaa, aab, ...).
- Novels: `PUT /novels/reorder` {orderedIds: [...]}.
- Dropped: scenes (CHAPTER_REQUIRES_CONVERSION, needs editor hash), custom chapter statuses (PRO, 403).

## Name-detection overrides
- `GET /characters/overrides/novel/{id}` list; `POST /characters/overrides` {novel_id (string), action: suppress|reassign, term, character_id (string, reassign only)} 201; `DELETE /characters/overrides/{id}` 204.
- Not implemented: `POST /characters/appearances` takes a client-computed `appearancesMap` (derived data); goals, `/home/todos` (PUT, max 8) and `/calendar` (needs `from`) were left out because probing them writes to the real account.

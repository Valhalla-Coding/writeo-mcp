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

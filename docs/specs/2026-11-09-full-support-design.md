# Writeo MCP: full support

Date: 2026-11-09. Extends `docs/design.md` (v0.1: login, novels, chapters, characters, notes, mood board).

## Goal

Claude can read and edit everything a writer can edit in Writeo, in the signed-in user's own account, as it already does for chapters, characters, notes and the mood board.

## Scope

In scope (writing content):

- Novels: update, reorder
- Volumes: list, create, update, delete
- Chapters: reorder; chapter statuses (list, create, update, delete)
- Scenes: list by chapter, create, update, delete, merge
- Characters: aliases and name tracking (`aliases`, `track_enabled`, `match_mode`, `require_capitalized`), profile sections, fields and values, templates, overrides, appearances, reorder of sections and fields
- Relationships: list (per novel, per character), create, update, delete
- Goals and goal progress, calendar events and reminders, home to-do list

Out of scope:

- Billing, account deletion, feature requests, streaks, achievements: not writing, and billing or account actions are not something an editing assistant should do.
- Deleting a whole novel: stays in Writeo itself (decided with the user).
- Any generic "call any route" tool.

## Findings

- Routes were listed from the site's own code. Resources: boards, calendar, chapter-statuses, chapters, characters, goals, home, notes, novels, relations, scenes, volumes (plus the out-of-scope ones above).
- A relation is created with `POST /relations`; the request uses `source_character_id`, `target_character_id` (strings), `relation_type` (max 15 characters, free text), `description`, `intensity` (1 to 10), `is_bidirectional`, `inverse_type`, `visibility`, `ai_context`, `motivation_impact`. The response uses different names (`character_source_id`, `character_target_id`). `is_bidirectional: true` makes two linked rows. `GET /relations/novel/{id}` returns `{nodes, links}`.
- Request shapes differ from response shapes, so each area's write format is captured from the real site before its tools are written. No guessing.

## Architecture

Unchanged: one small module per area over `client`, each a list of MCP tools. New modules: `tools_relations`, `tools_volumes`, `tools_scenes`, `tools_goals`, `tools_calendar`, `tools_todos`; `tools_characters` grows sections, fields, templates, aliases; `tools_chapters` grows statuses and reorder; `tools_novels` grows reorder. All route and field knowledge stays in the tool modules and `docs/api-notes.md`.

## Safety

- Every delete tool takes `confirm`. Without `confirm=true` it only reports what it would remove.
- Updates send only the fields given. Write tools return the saved record.
- Nothing in billing or account is exposed.
- Calls stay sequential.

## Capture method

For each area: create a scratch novel in the user's account, perform each action once through Writeo's own screens in the user's browser while recording request bodies and responses, then write the tool from the recording. The scratch novel is deleted on the site afterwards. Tokens are never printed or stored.

## Delivery in four rounds

Each round is tested, documented and pushed on its own so it can be used straight away.

1. Relationships, aliases, character sections, fields and templates.
2. Volumes, scenes, chapter statuses, reorder (novels, chapters, sections, fields).
3. Goals, calendar and reminders, to-dos.
4. Appearances, overrides, and anything the capture turns up.

## Testing

- Unit tests per area with recorded fixtures and a fake HTTP layer (as in v0.1).
- An opt-in live test on a scratch novel: create, edit, read back, delete.
- Delete tools are tested to do nothing without `confirm=true`.

## Risks

- Writeo is an unofficial target: routes can change. Failures name the route and status so the fix is local.
- The scratch-novel capture writes to the user's account; it is limited to one clearly named scratch novel.

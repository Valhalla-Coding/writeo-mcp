from datetime import date

from . import deps
from .client import WriteoError


def _brief(c: dict) -> dict:
    return {k: c.get(k) for k in ("id", "name", "role", "description")}


MATCH_MODES = ("auto", "substring")  # the two values Writeo accepted when probed


def _full(c: dict) -> dict:
    return {**_brief(c), **{k: c.get(k) for k in ("aliases", "track_enabled", "match_mode", "require_capitalized")}}


def _find(character_id: int, novel_id: int | None) -> dict:
    # Writeo has no fetch-by-id route for characters, so look in the novel's list.
    for c in deps.client.get(f"/characters/novel/{deps.need_novel(novel_id)}"):
        if c["id"] == character_id:
            return c
    raise WriteoError(f"Character {character_id} not found in that novel.")


def register(mcp):
    @mcp.tool()
    def list_characters(novel_id: int | None = None) -> list[dict]:
        """Characters of a novel."""
        return [_brief(c) for c in deps.client.get(f"/characters/novel/{deps.need_novel(novel_id)}")]

    @mcp.tool()
    def get_character(character_id: int, novel_id: int | None = None) -> dict:
        """One character, with the aliases Writeo tracks in the text and its tracking settings."""
        return _full(_find(character_id, novel_id))

    @mcp.tool()
    def create_character(name: str, description: str = "", role: str = "Side", novel_id: int | None = None) -> dict:
        """Add a character. Role is a label such as Main, Side or Antagonist. Portraits are not supported."""
        d = date.today()
        return _brief(deps.client.post("/characters", {
            "name": name, "image_url": "", "description": description, "role": role,
            "createdAt": f"{d.month}/{d.day}/{d.year}", "novel_id": str(deps.need_novel(novel_id)),
        }))

    @mcp.tool()
    def update_character(character_id: int, name: str | None = None, description: str | None = None,
                         role: str | None = None, aliases: list[str] | None = None,
                         track_enabled: bool | None = None, match_mode: str | None = None,
                         require_capitalized: bool | None = None) -> dict:
        """Change a character. Only the fields you give are changed. aliases replaces the whole list ([] clears it);
        match_mode is auto or substring."""
        if match_mode is not None and match_mode not in MATCH_MODES:
            raise WriteoError("match_mode must be auto or substring.")
        given = {"name": name, "description": description, "role": role, "aliases": aliases,
                 "track_enabled": track_enabled, "match_mode": match_mode, "require_capitalized": require_capitalized}
        return _full(deps.client.put(f"/characters/{character_id}", {k: v for k, v in given.items() if v is not None}))

    @mcp.tool()
    def delete_character(character_id: int, novel_id: int | None = None, confirm: bool = False) -> dict:
        """Delete a character. Without confirm=true this only shows what would be deleted."""
        character = _find(character_id, novel_id)
        if not confirm:
            return {"deleted": False, "would_delete": _brief(character), "next": "Call again with confirm=true to delete."}
        deps.client.delete(f"/characters/{character_id}")
        return {"deleted": True, "character": _brief(character)}

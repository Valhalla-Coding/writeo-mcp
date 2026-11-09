from . import deps
from .client import WriteoError


def _row(o: dict) -> dict:
    return {k: o.get(k) for k in ("id", "term", "action", "character_id")}


def register(mcp):
    @mcp.tool()
    def list_name_overrides(novel_id: int | None = None) -> list[dict]:
        """Rules that change how Writeo spots character names in the text: 'suppress' ignores a word,
        'reassign' makes a word count as a given character."""
        return [_row(o) for o in deps.client.get(f"/characters/overrides/novel/{deps.need_novel(novel_id)}")]

    @mcp.tool()
    def add_name_override(term: str, action: str, character_id: int | None = None, novel_id: int | None = None) -> dict:
        """Add a name-detection rule. action is 'suppress' (ignore `term`) or 'reassign' (count `term` as
        `character_id`, which is then required)."""
        if action not in ("suppress", "reassign"):
            raise WriteoError("action must be 'suppress' or 'reassign'.")
        if action == "reassign" and not character_id:
            raise WriteoError("reassign needs a character_id.")
        body = {"novel_id": str(deps.need_novel(novel_id)), "action": action, "term": term}
        if character_id:
            body["character_id"] = str(character_id)
        return _row(deps.client.post("/characters/overrides", body))

    @mcp.tool()
    def delete_name_override(override_id: int, confirm: bool = False, novel_id: int | None = None) -> dict:
        """Remove a name-detection rule. Without confirm=true this only shows the rule."""
        rules = deps.client.get(f"/characters/overrides/novel/{deps.need_novel(novel_id)}")
        rule = next((o for o in rules if o["id"] == override_id), None)
        if rule is None:
            raise WriteoError(f"Override {override_id} not found in that novel.")
        if not confirm:
            return {"deleted": False, "would_delete": _row(rule), "next": "Call again with confirm=true to delete."}
        deps.client.delete(f"/characters/overrides/{override_id}")
        return {"deleted": True, "override": _row(rule)}

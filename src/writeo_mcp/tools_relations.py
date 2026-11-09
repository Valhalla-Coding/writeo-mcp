from . import deps
from .client import WriteoError


def _check(relation_type: str | None, intensity: int | None):
    if relation_type is not None and not 1 <= len(relation_type) <= 15:
        raise WriteoError("relation_type must be 1 to 15 characters.")
    if intensity is not None and not 1 <= intensity <= 10:
        raise WriteoError("intensity must be between 1 and 10.")


def _graph(novel_id: int | None) -> tuple[list[dict], dict]:
    reply = deps.client.get(f"/relations/novel/{deps.need_novel(novel_id)}")
    return reply.get("links", []), {n["id"]: n["name"] for n in reply.get("nodes", [])}


def _row(link: dict, names: dict) -> dict:
    return {"id": link["id"], "from": names.get(link["source"]), "to": names.get(link["target"]),
            "from_id": link["source"], "to_id": link["target"], "type": link["type"],
            "description": link.get("description", ""), "intensity": link.get("intensity"),
            "mutual": bool(link.get("is_bidirectional"))}


def _saved(r: dict) -> dict:
    return {"id": r["id"], "from_id": r["character_source_id"], "to_id": r["character_target_id"],
            "type": r["relation_type"], "description": r.get("description", ""), "intensity": r.get("intensity"),
            "mutual": bool(r.get("is_bidirectional"))}


def _find(relation_id: int, links: list[dict]) -> dict:
    for link in links:
        if link["id"] == relation_id:
            return link
    raise WriteoError(f"Relation {relation_id} not found in that novel.")


def _no_duplicate(links: list[dict], source: int, target: int, relation_type: str, ignore: int | None = None):
    for link in links:
        if (link["source"], link["target"], link["type"]) == (source, target, relation_type) and link["id"] != ignore:
            raise WriteoError(f"That pair already has a '{relation_type}' relation (id {link['id']}). Edit it instead.")


def register(mcp):
    @mcp.tool()
    def list_relations(novel_id: int | None = None) -> list[dict]:
        """Relationships between the characters of a novel, with names."""
        links, names = _graph(novel_id)
        return [_row(link, names) for link in links]

    @mcp.tool()
    def create_relation(source_id: int, target_id: int, relation_type: str, description: str = "", intensity: int = 5,
                        mutual: bool = False, inverse_type: str | None = None, novel_id: int | None = None) -> dict:
        """Add a relation from one character to another, e.g. source is the 'father' of target. relation_type is
        up to 15 characters, intensity 1 to 10. mutual=true also adds the reverse (named inverse_type if given)."""
        _check(relation_type, intensity)
        links, _ = _graph(novel_id)
        _no_duplicate(links, source_id, target_id, relation_type)
        return _saved(deps.client.post("/relations", {
            "source_character_id": str(source_id), "target_character_id": str(target_id),
            "relation_type": relation_type, "description": description, "intensity": intensity,
            "is_bidirectional": mutual, "inverse_type": inverse_type, "visibility": "public",
            "ai_context": "", "motivation_impact": ""}))

    @mcp.tool()
    def update_relation(relation_id: int, relation_type: str | None = None, description: str | None = None,
                        intensity: int | None = None, novel_id: int | None = None) -> dict:
        """Change a relation. Only the fields you give are changed."""
        _check(relation_type, intensity)
        links, _ = _graph(novel_id)
        link = _find(relation_id, links)
        body = {k: v for k, v in {"relation_type": relation_type, "description": description,
                                  "intensity": intensity}.items() if v is not None}
        if not body:
            return {"changed": False, "note": "Nothing to change: give relation_type, description or intensity."}
        if relation_type is not None:
            _no_duplicate(links, link["source"], link["target"], relation_type, ignore=relation_id)
        return _saved(deps.client.put(f"/relations/{relation_id}", body))

    @mcp.tool()
    def delete_relation(relation_id: int, novel_id: int | None = None, confirm: bool = False) -> dict:
        """Delete a relation (a mutual one removes its reverse too). Without confirm=true this only shows what would be deleted."""
        links, names = _graph(novel_id)
        link = _find(relation_id, links)
        shown = {**_row(link, names), "note": "Also removes its reverse relation." if link.get("is_bidirectional") else ""}
        if not confirm:
            return {"deleted": False, "would_delete": shown, "next": "Call again with confirm=true to delete."}
        deps.client.delete(f"/relations/{relation_id}")
        return {"deleted": True, "relation": shown}

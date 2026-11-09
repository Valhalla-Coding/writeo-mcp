from . import deps
from .client import WriteoError


def _row(v: dict) -> dict:
    return {k: v.get(k) for k in ("id", "volume_number", "title", "description")}


def _find(volume_id: int, nid: int) -> dict:
    for v in deps.client.get(f"/volumes/novel/{nid}"):
        if v["id"] == volume_id:
            return v
    raise WriteoError(f"Volume {volume_id} not found in that novel.")


def register(mcp):
    @mcp.tool()
    def list_volumes(novel_id: int | None = None) -> list[dict]:
        """Volumes (the groups chapters sit in) of a novel, in order."""
        rows = deps.client.get(f"/volumes/novel/{deps.need_novel(novel_id)}")
        return [_row(v) for v in sorted(rows, key=lambda v: v.get("order_index") or 0)]

    @mcp.tool()
    def create_volume(title: str, novel_id: int | None = None) -> dict:
        """Add a volume after the existing ones."""
        nid = deps.need_novel(novel_id)
        number = max([v["volume_number"] for v in deps.client.get(f"/volumes/novel/{nid}")], default=0) + 1
        return _row(deps.client.post("/volumes", {"novel_id": str(nid), "title": title, "volume_number": number}))

    @mcp.tool()
    def rename_volume(volume_id: int, title: str, novel_id: int | None = None) -> dict:
        """Change a volume's title."""
        _find(volume_id, deps.need_novel(novel_id))
        return _row(deps.client.put(f"/volumes/{volume_id}", {"title": title}))

    @mcp.tool()
    def delete_volume(volume_id: int, confirm: bool = False, novel_id: int | None = None) -> dict:
        """Delete a volume. Without confirm=true this only shows it and how many chapters sit in it."""
        nid = deps.need_novel(novel_id)
        volume = _find(volume_id, nid)
        count = sum(1 for c in deps.client.get(f"/chapters/novel/{nid}") if c.get("volume_id") == volume_id)
        if not confirm:
            return {"deleted": False, "would_delete": _row(volume), "chapters_in_it": count,
                    "next": "Call again with confirm=true to delete."}
        deps.client.delete(f"/volumes/{volume_id}")
        return {"deleted": True, "volume": _row(volume), "chapters_in_it": count}

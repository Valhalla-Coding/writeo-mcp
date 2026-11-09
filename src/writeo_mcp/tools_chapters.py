from . import deps
from .client import WriteoError
from .convert import html_to_text, text_to_html


def _brief(c: dict) -> dict:
    return {k: c.get(k) for k in ("id", "title", "status", "word_count", "volume_id", "order_index")}


def _full(c: dict) -> dict:
    return {**_brief(c), "description": c.get("description"), "text": html_to_text(c.get("content"))}


def _volume_for_new_chapter(nid: int, volume_id: int | None) -> int:
    if volume_id:
        return volume_id
    volumes = deps.client.get(f"/volumes/novel/{nid}")
    if volumes:
        return max(volumes, key=lambda v: v["volume_number"])["id"]
    return deps.client.post("/volumes", {"title": "Volume One", "volume_number": 1, "novel_id": str(nid)})["id"]


def order_keys(n: int) -> list[str]:
    """n increasing lowercase keys ('aaa', 'aab', ...); Writeo sorts chapters by this string."""
    return ["".join(chr(97 + d) for d in (i // 676, i // 26 % 26, i % 26)) for i in range(n)]


def register(mcp):
    @mcp.tool()
    def list_chapters(novel_id: int | None = None) -> list[dict]:
        """Chapters of a novel in reading order (without their text)."""
        chapters = deps.client.get(f"/chapters/novel/{deps.need_novel(novel_id)}")
        return [_brief(c) for c in sorted(chapters, key=lambda c: (c.get("volume_id") or 0, c.get("order_index") or 0))]

    @mcp.tool()
    def get_chapter(chapter_id: int) -> dict:
        """One chapter with its text as plain paragraphs."""
        return _full(deps.client.get(f"/chapters/{chapter_id}"))

    @mcp.tool()
    def create_chapter(title: str, text: str = "", description: str = "",
                       novel_id: int | None = None, volume_id: int | None = None) -> dict:
        """Add a chapter at the end of a volume (the latest one by default; a first volume is created if none).
        Text is plain: blank lines separate paragraphs."""
        nid = deps.need_novel(novel_id)
        vol = _volume_for_new_chapter(nid, volume_id)
        in_volume = [c for c in deps.client.get(f"/chapters/novel/{nid}") if c.get("volume_id") == vol]
        created = deps.client.post("/chapters", {
            "title": title, "volume_id": vol, "description": description, "content": text_to_html(text),
            "order_index": len(in_volume) + 1, "parent_chapter_id": None, "novel_id": str(nid),
        })
        return _full(created)

    @mcp.tool()
    def update_chapter(chapter_id: int, title: str | None = None, text: str | None = None,
                       description: str | None = None, status: str | None = None) -> dict:
        """Change a chapter. Giving `text` replaces the whole chapter text. Only the fields you give are changed."""
        body = {k: v for k, v in {"title": title, "description": description, "status": status}.items() if v is not None}
        if text is not None:
            current = deps.client.get(f"/chapters/{chapter_id}")
            body["content"] = text_to_html(text)
            body["base_content_hash"] = current.get("content_hash")
        return _full(deps.client.put(f"/chapters/{chapter_id}", body))

    @mcp.tool()
    def delete_chapter(chapter_id: int, confirm: bool = False) -> dict:
        """Delete a chapter. Without confirm=true this only shows what would be deleted."""
        chapter = deps.client.get(f"/chapters/{chapter_id}")
        if not confirm:
            return {"deleted": False, "would_delete": _brief(chapter), "next": "Call again with confirm=true to delete."}
        deps.client.delete(f"/chapters/{chapter_id}")
        return {"deleted": True, "chapter": _brief(chapter)}

    @mcp.tool()
    def reorder_chapters(ordered_ids: list[int], novel_id: int | None = None) -> list[dict]:
        """Put the chapters in this order. ordered_ids must list every chapter of the novel exactly once."""
        nid = deps.need_novel(novel_id)
        have = {c["id"] for c in deps.client.get(f"/chapters/novel/{nid}")}
        if sorted(ordered_ids) != sorted(have):
            raise WriteoError(f"ordered_ids must be exactly the novel's chapter ids: {sorted(have)}.")
        for cid, key in zip(ordered_ids, order_keys(len(ordered_ids))):
            deps.client.patch(f"/chapters/{cid}/reorder", {"order_key": key, "novel_id": str(nid)})
        return [_brief(c) for c in sorted(deps.client.get(f"/chapters/novel/{nid}"), key=lambda c: c.get("order_key") or "")]

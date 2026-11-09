from . import deps
from .client import WriteoError
from .convert import doc_to_text, text_to_doc


def _brief(n: dict) -> dict:
    return {k: n.get(k) for k in ("id", "title", "category", "priority", "updated_at")}


def _full(n: dict) -> dict:
    return {**_brief(n), "text": doc_to_text(n.get("content"))}


def _find(note_id: int, novel_id: int | None) -> dict:
    for n in deps.client.get("/notes", params={"novel_id": deps.need_novel(novel_id)}):
        if n["id"] == note_id:
            return n
    raise WriteoError(f"Note {note_id} not found in that novel.")


def register(mcp):
    @mcp.tool()
    def list_notes(novel_id: int | None = None) -> list[dict]:
        """Notes of a novel (without their text)."""
        return [_brief(n) for n in deps.client.get("/notes", params={"novel_id": deps.need_novel(novel_id)})]

    @mcp.tool()
    def get_note(note_id: int, novel_id: int | None = None) -> dict:
        """One note with its text as plain lines."""
        return _full(_find(note_id, novel_id))

    @mcp.tool()
    def create_note(title: str, text: str = "", category: str = "worldbuilding", priority: str = "medium",
                    novel_id: int | None = None) -> dict:
        """Add a note. Text is plain, one paragraph per line. Category and priority are Writeo's labels, such as worldbuilding / medium."""
        return _full(deps.client.post("/notes", {
            "title": title, "content": text_to_doc(text), "category": category, "priority": priority,
            "novel_id": str(deps.need_novel(novel_id)), "character_ids": [], "chapter_ids": [], "tags": [],
            "is_pinned": False, "detail": "Rich text content", "type": category, "metadata": {"status": "To Do"},
        }))

    @mcp.tool()
    def update_note(note_id: int, title: str | None = None, text: str | None = None,
                    category: str | None = None, priority: str | None = None) -> dict:
        """Change a note. Giving `text` replaces the whole text. Only the fields you give are changed."""
        body = {k: v for k, v in {"title": title, "category": category, "priority": priority}.items() if v is not None}
        if text is not None:
            body["content"] = text_to_doc(text)
        return _full(deps.client.put(f"/notes/{note_id}", body))

    @mcp.tool()
    def delete_note(note_id: int, novel_id: int | None = None, confirm: bool = False) -> dict:
        """Delete a note. Without confirm=true this only shows what would be deleted."""
        note = _find(note_id, novel_id)
        if not confirm:
            return {"deleted": False, "would_delete": _brief(note), "next": "Call again with confirm=true to delete."}
        deps.client.delete(f"/notes/{note_id}")
        return {"deleted": True, "note": _brief(note)}

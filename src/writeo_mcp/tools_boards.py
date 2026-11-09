import uuid

from . import deps
from .client import WriteoError

# Node shapes as Writeo's own board editor saves them.
_KINDS = {
    "sticky": ("sticky", {"width": 200, "height": 200}),
    "text": ("free_text", {"width": 200}),
    "shape": ("shape", {"width": 150, "height": 150}),
}


def _text_of(node: dict) -> str:
    data = node.get("data") or {}
    return data.get("content") or data.get("label") or ""


def _item(node: dict) -> dict:
    pos = node.get("position") or {}
    return {"id": node["id"], "type": node.get("type"), "x": pos.get("x"), "y": pos.get("y"), "text": _text_of(node)}


def _save(board_id: str, board: dict, nodes: list) -> dict:
    return deps.client.put(f"/boards/{board_id}/canvas",
                           {"nodes": nodes, "edges": board.get("edges", []), "base_version": board.get("version", 0)})


def register(mcp):
    @mcp.tool()
    def list_boards(novel_id: int | None = None) -> list[dict]:
        """Story boards (mood boards) of a novel."""
        boards = deps.client.get("/boards", params={"novel_id": deps.need_novel(novel_id)})
        return [{k: b.get(k) for k in ("id", "title", "board_type", "updated_at")} for b in boards]

    @mcp.tool()
    def get_board(board_id: str) -> dict:
        """A board's items (sticky notes, text, shapes) with positions."""
        b = deps.client.get(f"/boards/{board_id}")
        return {"id": b["id"], "title": b.get("title"), "items": [_item(n) for n in b.get("nodes", [])],
                "connections": len(b.get("edges", []))}

    @mcp.tool()
    def add_board_item(board_id: str, kind: str = "sticky", text: str = "", x: float = 0, y: float = 0) -> dict:
        """Add a sticky note, a text box or a shape to a board. kind is sticky, text or shape. Text becomes the note text (or the shape label)."""
        if kind not in _KINDS:
            raise WriteoError("kind must be sticky, text or shape.")
        board = deps.client.get(f"/boards/{board_id}")
        node_type, style = _KINDS[kind]
        data = {"shapeType": "rectangle", "label": text} if kind == "shape" else {"content": text}
        node = {"id": str(uuid.uuid4()), "type": node_type, "position": {"x": x, "y": y},
                "style": dict(style), "data": data, "measured": dict(style)}
        _save(board_id, board, board.get("nodes", []) + [node])
        return _item(node)

    @mcp.tool()
    def update_board_item(board_id: str, item_id: str, text: str | None = None,
                          x: float | None = None, y: float | None = None) -> dict:
        """Change an item's text and/or move it. Only the fields you give are changed."""
        board = deps.client.get(f"/boards/{board_id}")
        nodes = board.get("nodes", [])
        node = next((n for n in nodes if n["id"] == item_id), None)
        if node is None:
            raise WriteoError(f"Item {item_id} not found on that board.")
        if text is not None:
            node["data"] = {**(node.get("data") or {}), "label" if node.get("type") == "shape" else "content": text}
        if x is not None or y is not None:
            pos = node.get("position") or {}
            node["position"] = {"x": pos.get("x", 0) if x is None else x, "y": pos.get("y", 0) if y is None else y}
        _save(board_id, board, nodes)
        return _item(node)

    @mcp.tool()
    def delete_board_item(board_id: str, item_id: str, confirm: bool = False) -> dict:
        """Remove an item from a board. Without confirm=true this only shows what would be removed."""
        board = deps.client.get(f"/boards/{board_id}")
        nodes = board.get("nodes", [])
        node = next((n for n in nodes if n["id"] == item_id), None)
        if node is None:
            raise WriteoError(f"Item {item_id} not found on that board.")
        if not confirm:
            return {"deleted": False, "would_delete": _item(node), "next": "Call again with confirm=true to delete."}
        _save(board_id, board, [n for n in nodes if n["id"] != item_id])
        return {"deleted": True, "item": _item(node)}

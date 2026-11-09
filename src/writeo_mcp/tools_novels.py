from datetime import date

from . import deps
from .client import WriteoError

_KEEP = ("id", "title", "status", "genre_v2", "chapters_count", "characters_count")


def _brief(n: dict) -> dict:
    return {**{k: n.get(k) for k in _KEEP}, "synopsis": n.get("description")}


def _today() -> str:
    d = date.today()
    return f"{d.month}/{d.day}/{d.year}"  # the format Writeo's own form sends


def register(mcp):
    @mcp.tool()
    def list_novels() -> list[dict]:
        """List the novels in the signed-in Writeo account."""
        return [_brief(n) for n in deps.client.get("/novels")]

    @mcp.tool()
    def select_novel(novel_id: int) -> dict:
        """Make this novel the current one. Other tools use it when no novel_id is given."""
        novel = deps.client.get(f"/novels/{novel_id}")
        deps.state.novel_id = novel_id
        return _brief(novel)

    @mcp.tool()
    def get_novel(novel_id: int | None = None) -> dict:
        """Details of a novel (the selected one by default)."""
        return _brief(deps.client.get(f"/novels/{deps.need_novel(novel_id)}"))

    @mcp.tool()
    def create_novel(title: str, synopsis: str = "", genres: list[str] | None = None) -> dict:
        """Create a novel and select it. Genres are names like Fantasy or Romance. Covers are not supported."""
        novel = deps.client.post("/novels", {
            "title": title, "genre_v2": genres or ["Fantasy"], "description": synopsis,
            "cover_image_url": "", "cover_focus_x": 0.5, "cover_focus_y": 0.5,
            "cover_fit": "cover", "created": _today(),
        })
        deps.state.novel_id = novel["id"]
        return _brief(novel)

    @mcp.tool()
    def update_novel(novel_id: int | None = None, title: str | None = None,
                     synopsis: str | None = None, genres: list[str] | None = None) -> dict:
        """Change a novel's title, synopsis or genres. Only the fields you give are changed."""
        body = {k: v for k, v in {"title": title, "description": synopsis, "genre_v2": genres}.items() if v is not None}
        return _brief(deps.client.put(f"/novels/{deps.need_novel(novel_id)}", body))

    @mcp.tool()
    def reorder_novels(ordered_ids: list[int]) -> list[dict]:
        """Put the novels in this order. ordered_ids must list every novel of the account exactly once."""
        have = {n["id"] for n in deps.client.get("/novels")}
        if sorted(ordered_ids) != sorted(have):
            raise WriteoError(f"ordered_ids must be exactly your novel ids: {sorted(have)}.")
        deps.client.put("/novels/reorder", {"orderedIds": ordered_ids})
        return [_brief(n) for n in deps.client.get("/novels")]

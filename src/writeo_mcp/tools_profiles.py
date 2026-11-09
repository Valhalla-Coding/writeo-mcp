import re

from . import deps
from .client import WriteoError


def _profile(character_id: int) -> dict:
    return deps.client.get(f"/characters/{character_id}/profile")


def _field(f: dict) -> dict:
    return {"id": f["id"], "label": f["field_label"], "key": f["field_key"], "type": f["field_type"], "value": f.get("value")}


def _find_section(profile: dict, section_id: int) -> dict:
    for s in profile.get("sections", []):
        if s["id"] == section_id:
            return s
    raise WriteoError(f"Section {section_id} not found on that character.")


def _find_field(profile: dict, field_id: int) -> tuple[dict, dict]:
    for s in profile.get("sections", []):
        for f in s.get("fields", []):
            if f["id"] == field_id:
                return s, f
    raise WriteoError(f"Field {field_id} not found on that character.")


def register(mcp):
    @mcp.tool()
    def get_character_profile(character_id: int) -> dict:
        """A character's profile: its sections with their fields and values."""
        p = _profile(character_id)
        return {"character": p["character"]["name"], "sections": [
            {"id": s["id"], "name": s["section_name"],
             "fields": [_field(f) for f in sorted(s.get("fields", []), key=lambda f: f.get("display_order") or 0)]}
            for s in p.get("sections", [])]}

    @mcp.tool()
    def add_profile_section(character_id: int, name: str) -> dict:
        """Add a profile section to a character."""
        s = deps.client.post("/characters/sections", {"character_id": str(character_id), "section_name": name})
        return {"id": s["id"], "name": s["section_name"]}

    @mcp.tool()
    def rename_profile_section(section_id: int, name: str) -> dict:
        """Rename a profile section."""
        s = deps.client.put(f"/characters/sections/{section_id}", {"section_name": name})
        return {"id": s["id"], "name": s["section_name"]}

    @mcp.tool()
    def reorder_profile_sections(character_id: int, section_ids: list[int]) -> dict:
        """Put a character's sections in this order. Give every section id."""
        deps.client.put("/characters/sections/reorder", {"characterId": character_id, "orderedIds": section_ids})
        return {"order": section_ids}

    @mcp.tool()
    def delete_profile_section(character_id: int, section_id: int, confirm: bool = False) -> dict:
        """Delete a profile section and its fields. Without confirm=true this only shows what would be deleted."""
        s = _find_section(_profile(character_id), section_id)
        shown = {"id": s["id"], "name": s["section_name"], "fields": len(s.get("fields", []))}
        if not confirm:
            return {"deleted": False, "would_delete": shown, "next": "Call again with confirm=true to delete."}
        deps.client.delete(f"/characters/sections/{section_id}")
        return {"deleted": True, "section": shown}

    @mcp.tool()
    def add_profile_field(character_id: int, section_id: int, label: str, value: str = "", field_type: str = "text") -> dict:
        """Add a field to a profile section, with an optional first value."""
        key = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_") or "field"
        f = deps.client.post("/characters/fields", {"section_id": section_id, "field_key": key,
                                                    "field_label": label, "field_type": field_type})
        if value:
            deps.client.post("/characters/values", {"character_id": character_id, "field_def_id": f["id"],
                                                    "value": value, "context": {}})
        return {**_field(f), "value": value or None}

    @mcp.tool()
    def set_profile_value(character_id: int, field_id: int, value: str) -> dict:
        """Set the value of a profile field (replaces the old value)."""
        v = deps.client.post("/characters/values", {"character_id": character_id, "field_def_id": field_id,
                                                    "value": value, "context": {}})
        return {"field_id": v["field_def_id"], "value": v["value"]}

    @mcp.tool()
    def rename_profile_field(field_id: int, label: str) -> dict:
        """Change a profile field's label."""
        f = deps.client.put(f"/characters/fields/{field_id}", {"field_label": label})
        return {"id": f["id"], "label": f["field_label"]}

    @mcp.tool()
    def reorder_profile_fields(field_ids: list[int]) -> dict:
        """Put the fields of one section in this order. Give every field id of that section."""
        deps.client.put("/characters/fields/reorder", {"updates": [{"id": i, "display_order": n} for n, i in enumerate(field_ids)]})
        return {"order": field_ids}

    @mcp.tool()
    def delete_profile_field(character_id: int, field_id: int, confirm: bool = False) -> dict:
        """Delete a profile field and its value. Without confirm=true this only shows what would be deleted."""
        s, f = _find_field(_profile(character_id), field_id)
        shown = {"id": f["id"], "label": f["field_label"], "section": s["section_name"], "value": f.get("value")}
        if not confirm:
            return {"deleted": False, "would_delete": shown, "next": "Call again with confirm=true to delete."}
        deps.client.request("DELETE", "/characters/fields", json={"fieldIds": [field_id]})
        return {"deleted": True, "field": shown}

    @mcp.tool()
    def list_profile_templates() -> list[dict]:
        """Profile section templates Writeo offers (applying one is done in Writeo itself)."""
        return [{"id": t["id"], "name": t["name"], "description": t.get("description", ""),
                 "fields": [d["field_label"] for d in t.get("field_definitions", [])]}
                for t in deps.client.get("/characters/templates/all")]

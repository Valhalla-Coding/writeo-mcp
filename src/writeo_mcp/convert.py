"""Plain text <-> the formats Writeo stores: HTML for chapters, ProseMirror JSON for notes."""
import html
import json
import re


def text_to_html(text: str) -> str:
    blocks = [b for b in re.split(r"\n\s*\n", text.strip()) if b.strip()]
    return "".join("<p>" + html.escape(b.strip()).replace("\n", "<br>") + "</p>" for b in blocks)


def html_to_text(markup: str | None) -> str:
    if not markup:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", markup)
    s = re.sub(r"</(p|h[1-6]|li|blockquote|div)>", "\n\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\n{3,}", "\n\n", html.unescape(s)).strip()


def text_to_doc(text: str) -> dict:
    """One paragraph per non-empty line."""
    paras = [{"type": "paragraph", "content": [{"type": "text", "text": line}]}
             for line in text.splitlines() if line.strip()]
    return {"type": "doc", "content": paras or [{"type": "paragraph"}]}


def _lines(node: dict) -> list[str]:
    t = node.get("type")
    if t == "text":
        return [node.get("text", "")]
    if t == "hardBreak":
        return ["\n"]
    kids = node.get("content", [])
    if t in ("paragraph", "heading", "codeBlock"):
        return ["".join(s for k in kids for s in _lines(k))]
    return [line for k in kids for line in _lines(k)]


def doc_to_text(doc) -> str:
    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except ValueError:
            return doc
    if not isinstance(doc, dict):
        return ""
    return "\n".join(_lines(doc)).strip()

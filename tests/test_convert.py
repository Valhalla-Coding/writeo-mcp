from writeo_mcp.convert import doc_to_text, html_to_text, text_to_doc, text_to_html


def test_text_to_html_paragraphs_breaks_and_escaping():
    assert text_to_html("one\n\ntwo\nthree & <b>") == "<p>one</p><p>two<br>three &amp; &lt;b&gt;</p>"


def test_html_roundtrip():
    text = "First paragraph.\n\nSecond line\nbroken."
    assert html_to_text(text_to_html(text)) == text


def test_html_to_text_empty():
    assert html_to_text(None) == ""


def test_doc_roundtrip_and_string_form():
    doc = text_to_doc("a\nb")
    assert doc_to_text(doc) == "a\nb"
    import json
    assert doc_to_text(json.dumps(doc)) == "a\nb"


def test_doc_to_text_nested_list():
    doc = {"type": "doc", "content": [{"type": "bulletList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "y"}]}]}]}]}
    assert doc_to_text(doc) == "x\ny"

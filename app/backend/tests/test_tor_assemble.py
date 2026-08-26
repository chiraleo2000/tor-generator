"""Assemble TOR rows without s4.s4.1 keys or parent overwrite."""

from types import SimpleNamespace

from app.services.tor_assemble import assemble_review_document, document_section_key


def test_document_section_key_never_nests_s4():
    assert document_section_key("s4", None) == "s4"
    assert document_section_key("s4", "s4.1") == "s4.1"
    assert document_section_key("s4", "1") == "s4.1"
    assert document_section_key("s4", "s4") == "s4"
    assert document_section_key("s4", "4.2") == "s4.2"
    assert document_section_key("", "3") == "s3"
    assert document_section_key("s8", "note") == "s8.note"
    assert document_section_key("s1", None) == "s1"


def test_assemble_keeps_parent_and_sub_keys_separate():
    rows = [
        SimpleNamespace(section_key="s4", sub_key=None, content="สรุปขอบเขตสั้น"),
        SimpleNamespace(section_key="s4", sub_key="s4.1", content="งานหลักของโครงการ"),
        SimpleNamespace(section_key="s1", sub_key=None, content="ความเป็นมาของหน่วยงาน"),
    ]
    document, parents = assemble_review_document(rows)
    assert "s4.s4.1" not in document
    assert document["s4.1"] == "งานหลักของโครงการ"
    assert document["s4"] == "สรุปขอบเขตสั้น"
    assert parents["s4"] == "สรุปขอบเขตสั้น"
    assert "s4.1" not in parents
    assert document["s1"] == "ความเป็นมาของหน่วยงาน"

from app.domain.section_fields import parse_section_fields, persist_section_fields


def test_parse_markdown_headings_with_trailing_spaces() -> None:
    raw = "### history  \nระบบเดิม\n### problems\nซ่อมบ่อย"
    assert parse_section_fields("s1", raw) == {
        "history": "ระบบเดิม",
        "problems": "ซ่อมบ่อย",
    }


def test_persist_structured_fields_as_json() -> None:
    raw = persist_section_fields("s1", "### history\nระบบเดิม")
    assert raw == '{"history": "ระบบเดิม"}'


def test_parse_thai_field_labels_without_hashes() -> None:
    raw = (
        "ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม\n"
        "ระบบงานเดิมใช้เอกสารกระดาษ\n"
        "ปัญหาที่พบ (ระบุตัวเลข/สถิติ)\n"
        "ซ่อมบ่อยปีละ ๑๒ ครั้ง\n"
        "นโยบาย/กฎหมายที่เกี่ยวข้อง\n"
        "พ.ร.บ. การจัดซื้อจัดจ้าง พ.ศ. ๒๕๖๐"
    )
    parsed = parse_section_fields("s1", raw)
    assert parsed["history"] == "ระบบงานเดิมใช้เอกสารกระดาษ"
    assert parsed["problems"] == "ซ่อมบ่อยปีละ ๑๒ ครั้ง"
    assert "๒๕๖๐" in parsed["policy"]


def test_migrate_body_blob_into_first_field() -> None:
    raw = persist_section_fields("s1", '{"body": "โครงการจัดซื้อระบบคอมพิวเตอร์"}')
    assert '"history"' in raw
    assert "body" not in raw
    assert "โครงการจัดซื้อระบบคอมพิวเตอร์" in raw


def test_parse_empty_and_invalid_json_and_paragraphs() -> None:
    assert parse_section_fields("s1", "  ") == {}
    fallback = parse_section_fields("s1", "{not-json")
    assert fallback["history"].startswith("{not-json")
    paras = parse_section_fields(
        "s1",
        "ย่อหน้าประวัติระบบเดิม\n\nย่อหน้าปัญหาที่พบ\n\nย่อหน้านโยบาย",
    )
    assert paras["history"] == "ย่อหน้าประวัติระบบเดิม"
    assert paras["problems"] == "ย่อหน้าปัญหาที่พบ"
    assert "นโยบาย" in paras["policy"]


def test_parse_json_object_fields() -> None:
    parsed = parse_section_fields(
        "s1",
        '{"history": "ระบบเดิม", "problems": "ซ่อมบ่อย"}',
    )
    assert parsed == {"history": "ระบบเดิม", "problems": "ซ่อมบ่อย"}

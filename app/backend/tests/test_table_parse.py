"""Tests for markdown table / scope subsection parsing."""

from app.export.table_parse import parse_markdown_table_rows, split_scope_subsection_draft
from app.services.thai_draft import scope_overview_from_subs, split_content_blocks


def test_parse_markdown_table_rows():
    lines = [
        "| รายการ | จำนวน |",
        "| --- | --- |",
        "| เซิร์ฟเวอร์ | 2 |",
    ]
    rows = parse_markdown_table_rows(lines)
    assert rows is not None
    assert rows[0] == ["รายการ", "จำนวน"]
    assert rows[1] == ["เซิร์ฟเวอร์", "2"]


def test_is_table_separator_and_short_input():
    from app.export.table_parse import is_table_separator

    assert is_table_separator("| --- | :---: |")
    assert not is_table_separator("| ชื่อ | ค่า |")
    assert not is_table_separator("ไม่มีท่อ")
    assert parse_markdown_table_rows(["| ก | ข |"]) is None


def test_parse_unprefixed_pipe_rows():
    rows = parse_markdown_table_rows(
        [
            "รายการ | จำนวน",
            "--- | ---",
            "เซิร์ฟเวอร์ | 2",
        ]
    )
    assert rows is not None
    assert rows[0][0] == "รายการ"
    assert rows[-1][-1] == "2"


def test_split_text_blocks_detects_table():
    from app.export.table_parse import split_text_blocks

    blocks = split_text_blocks("คำนำ\n| ก | ข |\n| --- | --- |\n| 1 | 2 |\nท้าย")
    kinds = [kind for kind, _lines in blocks]
    assert "table" in kinds
    assert "para" in kinds


def test_split_scope_heading_without_s_prefix():
    parts = split_scope_subsection_draft("### 4.2 ระบบเดิม\nรายละเอียดงานปัจจุบัน")
    assert "s4.2" in parts
    assert "ระบบเดิม" in parts["s4.2"]
    assert parts["s4.2"].endswith("รายละเอียดงานปัจจุบัน")


def test_split_scope_subsection_draft():
    text = (
        "### s4.1\nสรุปงานหลัก\n\n"
        "### s4.3\n"
        "| รายการ | จำนวน |\n"
        "| --- | --- |\n"
        "| เครื่อง | 1 |\n"
    )
    parts = split_scope_subsection_draft(text)
    assert "สรุปงานหลัก" in parts["s4.1"]
    assert "เครื่อง" in parts["s4.3"]


def test_scope_overview_is_short_not_full_merge():
    overview = scope_overview_from_subs(
        {
            "s4.1": "ก" * 500,
            "s4.3": "งานติดตั้ง",
        }
    )
    assert "รายละเอียดครบในหัวข้อย่อย" in overview
    assert "งานติดตั้ง" not in overview
    assert len(overview) < 450


def test_split_content_blocks_tables():
    text = "คำนำ\n| ก | ข |\n| --- | --- |\n| 1 | 2 |\nท้าย"
    blocks = split_content_blocks(text)
    kinds = [b[0] for b in blocks]
    assert "table" in kinds
    assert "para" in kinds


def test_merge_scope_and_sub_prompt_are_thai():
    from app.services.thai_draft import merge_scope_from_subs, scope_sub_prompt

    merged = merge_scope_from_subs({"s4.1": "วิเคราะห์ความต้องการและพัฒนาโมดูล", "s4.2": ""})
    assert "๔.1" in merged or "๔." in merged
    assert "วิเคราะห์ความต้องการ" in merged
    prompt = scope_sub_prompt(
        "s4.8",
        {"s4.8": {"content": "ส่งมอบคู่มือ", "status": "filled"}},
        rag_context="พ.ร.บ. การจัดซื้อจัดจ้าง",
    )
    assert "ภาษาไทย" in prompt
    assert "ส่งมอบคู่มือ" in prompt
    assert "พ.ร.บ." in prompt
    assert "6144" in prompt
    assert "กระชับ" not in prompt
    current = scope_sub_prompt("s4.2", {}, "")
    assert "ระบบงานปัจจุบัน" in current
    assert "As-Is System" not in current

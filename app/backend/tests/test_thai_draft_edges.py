"""License-table and scope-prompt branches added in the draft helper split."""

from app.services.thai_draft import (
    _consume_license_line,
    _ict_use_value,
    _LicenseBuild,
    _license_reason,
    _normalize_license_data_row,
    _table_placeholder_end,
    is_scope_content_wrong_owner,
    normalize_license_ict_table,
    sanitize_scope_draft_tables,
    scope_sub_prompt,
    strip_manual_section_numbers,
)


def test_license_table_edges_cover_totals_reasons_and_placeholders():
    assert _ict_use_value("", "  ") == ""
    assert _ict_use_value("ไม่") == "ไม่ใช้"
    assert normalize_license_ict_table("") == ""
    assert normalize_license_ict_table("ไม่มีตารางลิขสิทธิ์") == "ไม่มีตารางลิขสิทธิ์"
    raw = "\n".join(
        [
            "หมายเหตุลิขสิทธิ์ซอฟต์แวร์",
            "[Table 2]",
            "ลำดับ | รายการ | จำนวนสิทธิ์ | ราคาต่อหน่วย (บาท) | ราคารวม (บาท) | ใช้ | ไม่ใช้ | เหตุผล",
            "1 | แท็บเล็ต | 10 | 1000 | 10000 |  | ใช้ | เพราะไม่มีเกณฑ์",
            "1 | แท็บเล็ต | 10 | 1000 | 10000 |  | ใช้ | เพราะไม่มีเกณฑ์",
            "รวม |  |  |  | 10000 |  |  | ",
            "licenses ซ้ำ",
            "ครุภัณฑ์และลิขสิทธิ์ซอฟต์แวร์",
        ]
    )
    table = normalize_license_ict_table(raw)
    assert table.startswith("| ลำดับ |") or "แท็บเล็ต" in table
    assert _license_reason(
        ["1", "ของ", "1", "2", "3", "4", "5", "เหตุผลท้าย"],
        ["1", "ของ", "1", "2", "3", "4", "5", "เหตุผลท้าย"],
        "ใช้",
    ) == "เหตุผลท้าย"
    assert _normalize_license_data_row(["---", "---"]) is None
    assert _normalize_license_data_row(["ไม่ใช่แถว"]) is None
    build = _LicenseBuild()
    _consume_license_line(build, "   ")
    _consume_license_line(build, "ข้อความนำหน้า")
    assert "ข้อความนำหน้า" in build.preface
    cleaned = sanitize_scope_draft_tables("[ Table ๑ ]\nบรรทัด")
    assert "Table" not in cleaned
    assert _table_placeholder_end("ไม่ใช่", 0) is None
    assert strip_manual_section_numbers("") == ""
    spaced = "1  รายการสิทธิ์  10"
    assert "รายการสิทธิ์" in strip_manual_section_numbers(spaced)


def test_scope_prompt_includes_prior_feedback_and_rejects_wrong_owner():
    slot_map = {
        "licenses": {"content": "รายการสิทธิ์จากเอกสาร", "status": "filled"},
        "s4": {"content": "ขอบเขตทั้งหมวด", "status": "filled"},
        "_project_intake": {"content": "เอกสารขั้นที่ ๐", "status": "filled"},
    }
    prompt = scope_sub_prompt(
        "licenses",
        slot_map,
        rag_context="พระราชบัญญัติ",
        category="hire_develop",
        current_draft="ร่างลิขสิทธิ์เดิม",
        user_feedback="ให้เหลือเฉพาะตาราง",
    )
    assert "ร่างปัจจุบัน" in prompt
    assert "ความคิดเห็นจากผู้ใช้" in prompt
    assert "พระราชบัญญัติ" in prompt
    assert is_scope_content_wrong_owner(
        "licenses",
        "ขอบเขตและวิธีการดำเนินงาน\nข้อกำหนดทั่วไป",
    )
    assert is_scope_content_wrong_owner("", "มีข้อความ") is False
    no_facts = scope_sub_prompt(
        "testing",
        {"_project_intake": {"content": "เอกสารขั้นที่ ๐ ยาว", "status": "filled"}},
        category="hire_develop",
    )
    assert "เอกสารขั้นที่ ๐" in no_facts

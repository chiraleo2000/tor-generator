"""Tests for scope subsection polish and ownership prompts."""

from app.services.thai_draft import (
    LICENSE_ICT_TABLE_TEMPLATE,
    polish_scope_subsection_draft,
    scope_sub_ownership_block,
    scope_sub_prompt,
    strip_manual_section_numbers,
)


def test_strip_manual_section_numbers_mixed_thai_arabic():
    raw = (
        "8.๑ ข้อกำหนดทั่วไป\n"
        "8.๑.๑ ระบบงานที่พัฒนาต้องทำงานภายใต้ฐานข้อมูล\n"
        "๘.๒ การบันทึกและนำเข้าข้อมูล\n"
        "| ลำดับ | รายการ |\n"
        "| --- | --- |\n"
        "| ๑ | สิทธิ์ |\n"
    )
    cleaned = strip_manual_section_numbers(raw)
    assert "8.๑" not in cleaned
    assert "๘.๒" not in cleaned
    assert cleaned.startswith("ข้อกำหนดทั่วไป")
    assert "| ลำดับ | รายการ |" in cleaned


def test_polish_drops_table_placeholder_and_dup_header():
    raw = (
        "ครุภัณฑ์และลิขสิทธิ์ซอฟต์แวร์ที่ต้องจัดหา\n"
        "[Table 5]\n"
        "| ลำดับ | รายการ | จำนวน License |\n"
        "| --- | --- | --- |\n"
        "| ลำดับ | รายการ | จำนวน License |\n"
        "| ๑ | ซอฟต์แวร์ | ๑๐ |\n"
    )
    cleaned = polish_scope_subsection_draft(raw)
    assert "Table" not in cleaned
    assert cleaned.count("ลำดับ | รายการ") == 1
    assert "ซอฟต์แวร์" in cleaned


def test_testing_prompt_forbids_method_leakage():
    prompt = scope_sub_prompt(
        "testing",
        {
            "testing": {
                "content": "แผนทดสอบ UAT และเกณฑ์ผ่าน",
                "status": "filled",
            },
        },
        category="hire_develop",
    )
    assert "ห้ามใส่ขอบเขตและวิธีการดำเนินงาน" in prompt
    assert "แผนทดสอบ UAT" in prompt
    assert "8.1" in prompt or "๘.๑" in prompt


def test_licenses_prompt_includes_ict_table_template():
    prompt = scope_sub_prompt("licenses", {}, category="hire_develop")
    assert "เกณฑ์กลาง ICT" in prompt
    assert LICENSE_ICT_TABLE_TEMPLATE.splitlines()[0] in prompt
    assert "[Table" in scope_sub_ownership_block("licenses", "ลิขสิทธิ์")


def test_normalize_license_tsv_to_markdown_table():
    from app.services.thai_draft import normalize_license_ict_table

    raw = (
        "ครุภัณฑ์และลิขสิทธิ์ซอฟต์แวร์ที่ต้องจัดหา\n"
        "ลำดับ\tรายการ\tจำนวน\tราคาต่อหน่วย\tราคารวม\tเกณฑ์กลาง ICT\tกรณีไม่ใช้เกณฑ์กลางให้ระบุเหตุผล\n"
        "\t\t\t\t\tใช้\tไม่ใช้\t\n"
        "1\tคอมพิวเตอร์แท็บเล็ต แบบที่ 2\t40\t22,000\t880,000\t\n"
        "ลำดับ\tรายการ\tจำนวน\tราคาต่อหน่วย\tราคารวม\tเกณฑ์กลาง ICT\tกรณีไม่ใช้เกณฑ์กลางให้ระบุเหตุผล\n"
        "\t\t\t\t\tใช้\tไม่ใช้\t\n"
        "1\tคอมพิวเตอร์แท็บเล็ต แบบที่ 2\t40\t22,000\t880,000\t\t\t\n"
    )
    cleaned = polish_scope_subsection_draft(raw, "licenses")
    assert cleaned.startswith("| ลำดับ |")
    assert cleaned.count("คอมพิวเตอร์แท็บเล็ต") == 1
    assert "| ใช้ |" in cleaned or "| ใช้ |" in cleaned.replace("  ", " ")
    assert "ใช้เกณฑ์กลาง ICT" in cleaned
    assert "\t" not in cleaned
    assert normalize_license_ict_table(raw).count("\n| 1 |") == 1
